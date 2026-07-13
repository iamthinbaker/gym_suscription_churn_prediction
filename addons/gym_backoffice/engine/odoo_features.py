"""
Construcción del dataset de churn a partir de recordsets de Odoo
(``res.partner`` + sus relaciones ``gym.access`` / ``gym.engagement``).

Se usa tanto al entrenar (``wizards.gym_churn_trainer``,
``wizards.gym_churn_survival_trainer``) como al puntuar (cron diario en
``models.gym_customer_health``) — mismo código en ambos casos para evitar
divergencias entre las features de entrenamiento y las de inferencia
("train/serve skew").
"""

from __future__ import annotations

from datetime import date

import pandas as pd


class PartnerFeatureBuilder:
    """Construye, por socio, las variables que consumen ``ChurnProbabilityModel``
    y ``ChurnSurvivalModel``.

    No reutiliza ``engine.feature_engineering.FeatureEngineer``, que está
    pensada para el dataset sintético de 17 tablas del notebook — el
    esquema real de Odoo es mucho más reducido.
    """

    def _rows(self, partners) -> pd.DataFrame:
        today = date.today()
        rows = []

        for partner in partners:
            accesses = partner.access_log_ids
            engagements = partner.engagement_ids

            check_ins = [a.check_in.date() for a in accesses if a.check_in]
            visits_7d = sum(1 for d in check_ins if (today - d).days <= 7)
            visits_30d = sum(1 for d in check_ins if (today - d).days <= 30)
            visits_90d = sum(1 for d in check_ins if (today - d).days <= 90)
            days_since_last_visit = (today - max(check_ins)).days if check_ins else 999

            durations = [a.duration for a in accesses if a.duration]
            avg_duration = sum(durations) / len(durations) if durations else 0.0
            n_activity_types = len({a.activity_type for a in accesses if a.activity_type})

            engagement_dates = [e.date for e in engagements if e.date]
            ratings = [int(e.rating) for e in engagements if e.rating]
            avg_rating = sum(ratings) / len(ratings) if ratings else 0.0
            days_since_last_engagement = (
                (today - max(engagement_dates)).days if engagement_dates else 999
            )

            antiguedad_dias = (
                (today - partner.membership_start).days if partner.membership_start else None
            )

            rows.append({
                "partner_id": partner.id,
                "member_status": partner.member_status,
                "membership_type": partner.membership_type,
                "gym_center": partner.gym_center_id.name or "Sin centro",
                "antiguedad_dias": antiguedad_dias,
                "visitas_ultimos_7_dias": visits_7d,
                "visitas_ultimos_30_dias": visits_30d,
                "visitas_ultimos_90_dias": visits_90d,
                "ratio_visitas_7_30": visits_7d / (visits_30d + 1),
                "ratio_visitas_30_90": visits_30d / (visits_90d + 1),
                "dias_desde_ultima_visita": days_since_last_visit,
                "duracion_media_sesion": avg_duration,
                "n_tipos_actividad_access": n_activity_types,
                "n_engagements": len(engagements),
                "valoracion_media_actividades": avg_rating,
                "dias_desde_ultimo_engagement": days_since_last_engagement,
            })

        return pd.DataFrame(rows).set_index("partner_id")

    def build(self, partners) -> tuple[pd.DataFrame, pd.Series]:
        """Features + target para ``ChurnProbabilityModel``: ``y`` es 1 si
        el socio está dado de baja (clasificación)."""
        df = self._rows(partners)
        y = (df.pop("member_status") == "churned").astype(int)
        return df, y

    def build_survival(self, partners) -> tuple[pd.DataFrame, pd.DataFrame]:
        """Features + target para ``ChurnSurvivalModel``: ``y`` tiene las
        columnas ``duration`` (antigüedad en meses) y ``event`` (1 = baja
        observada, 0 = censurado / activo).

        Excluye ``antiguedad_dias`` de ``X`` — es la propia ``duration``
        expresada en días, incluirla como feature sería fuga de datos
        (mismo motivo por el que el notebook excluye ``num_renovaciones``,
        ver ``experiments/churn_survival_prediction.ipynb``)."""
        df = self._rows(partners)
        event = (df.pop("member_status") == "churned").astype(int)
        antiguedad_dias = df.pop("antiguedad_dias")
        duration = (antiguedad_dias / 30.0).clip(lower=0.5).fillna(0.5)
        y = pd.DataFrame({"duration": duration, "event": event})
        return df, y

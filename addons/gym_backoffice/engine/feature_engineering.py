"""
Feature engineering para el pipeline de churn, extraído de
``experiments/churn_prediction.ipynb``.

``FeatureEngineer`` toma el DataFrame maestro ya mergeado (``contactos`` +
el resto de módulos + ``centros_deportivos``, con ``suffixes=('', '_centro')``)
y devuelve el DataFrame final de features, listo para entrar directamente en
``ChurnModel`` (ver ``engine/churn_model.py``).
"""

from __future__ import annotations

from datetime import date

import pandas as pd

# Columnas que no pueden clasificarse por dtype: identificadores, texto libre,
# fechas en crudo sin uso en el feature engineering, y el target.
EXCLUDE_FEATURES = [
    "cliente_id", "centro_id", "entrenador_asignado_id", "codigo_postal", "id",
    "nombre", "apellidos", "ciudad", "comentarios", "nombre_centro", "ciudad_centro", "director",
    "fecha_nacimiento", "fecha_primera_visita", "fecha_conversion",
    "fecha_inicio", "fecha_proxima_renovacion", "ultima_subida_precio",
    "ultimo_pago", "ultima_incidencia", "fecha_apertura", "fecha_apertura_competidor", "horario",
    "estado", "churn",
]

# Columnas crudas ya absorbidas en las variables engineered: se eliminan para
# no duplicar señal.
ABSORBED_BY_ENGINEERING = [
    "emails_enviados", "emails_abiertos",
    "sms_enviados", "sms_abiertos",
    "campanas_recibidas", "campanas_convertidas",
    "valoracion_entrenador", "valoracion_instalaciones",
    "valoracion_limpieza", "valoracion_clases",
    "fecha_alta", "fecha_alta_dt",
]


def build_target(df: pd.DataFrame) -> pd.Series:
    """Deriva la etiqueta de churn a partir de la columna ``estado``."""
    return (df["estado"] == "Baja").astype(int)


class FeatureEngineer:
    """Construye las variables derivadas y selecciona el conjunto final de
    features a partir del DataFrame maestro en crudo.

    A diferencia del notebook (que fija ``TODAY`` una vez al iniciar el
    kernel), aquí se recalcula ``date.today()`` en cada llamada a
    ``transform`` — es lo correcto para un modelo que corre en producción a
    lo largo del tiempo.
    """

    def transform(self, df: pd.DataFrame) -> pd.DataFrame:
        d = df.copy()
        today = date.today()

        # Actividad
        d["ratio_visitas_7_30"] = d["visitas_ultimos_7_dias"] / (d["visitas_ultimos_30_dias"] + 1)
        d["ratio_visitas_30_90"] = d["visitas_ultimos_30_dias"] / (d["visitas_ultimos_90_dias"] + 1)
        d["ratio_clases_canceladas"] = d["clases_canceladas_mes"] / (d["clases_reservadas_mes"] + 1)

        # Marketing
        d["tasa_apertura_email"] = d["emails_abiertos"] / (d["emails_enviados"] + 1)
        d["tasa_apertura_sms"] = d["sms_abiertos"] / (d["sms_enviados"] + 1)
        d["tasa_conv_campanas"] = d["campanas_convertidas"] / (d["campanas_recibidas"] + 1)

        # Facturación
        d["ratio_precio_uso"] = d["precio_mensual"] / (d["visitas_ultimos_30_dias"] + 1)
        d["total_incidencias_pago"] = (
            d["num_pagos_rechazados"] + d["retrasos_en_pagos"] + d["cuotas_pendientes"]
        )

        # Antigüedad en días
        d["fecha_alta_dt"] = pd.to_datetime(d["fecha_alta"], errors="coerce")
        d["antiguedad_dias"] = (pd.Timestamp(today) - d["fecha_alta_dt"]).dt.days

        # Encuestas
        enc = ["valoracion_entrenador", "valoracion_instalaciones", "valoracion_limpieza", "valoracion_clases"]
        d["satisfaccion_media"] = d[enc].mean(axis=1)
        d["sin_encuesta"] = d["nps"].isna().astype(int)

        # Helpdesk
        d["incidencia_grave"] = ((d["reclamaciones"] > 0) | (d["incidencias_abiertas"] > 1)).astype(int)

        d = d.drop(columns=[c for c in ABSORBED_BY_ENGINEERING if c in d.columns])
        d = d.drop(columns=[c for c in EXCLUDE_FEATURES if c in d.columns], errors="ignore")

        return d

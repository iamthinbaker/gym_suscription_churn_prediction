import base64
import logging
import os
import tempfile
from datetime import date, timedelta

from odoo import api, fields, models
from odoo.exceptions import UserError

from ..engine.churn_probability_model import ChurnProbabilityModel
from ..engine.churn_survival_model import ChurnSurvivalModel
from ..engine.odoo_features import PartnerFeatureBuilder

_logger = logging.getLogger(__name__)


class GymCustomerHealth(models.Model):
    _name = "gym.customer.health"
    _description = "Health Score del Socio"
    _order = "date desc"
    _rec_name = "display_name"

    partner_id = fields.Many2one(
        "res.partner",
        string="Socio",
        required=True,
        domain=[("is_gym_member", "=", True)],
    )
    date = fields.Date(string="Fecha del análisis", default=fields.Date.today)

    visits_last_30_days = fields.Integer(string="Visitas (30 días)")
    visits_last_60_days = fields.Integer(string="Visitas (60 días)")
    visits_last_90_days = fields.Integer(string="Visitas (90 días)")
    days_since_last_visit = fields.Integer(string="Días sin visitar")
    avg_weekly_visits = fields.Float(string="Media semanal de visitas", digits=(5, 2))
    engagement_score = fields.Float(string="Engagement Score (0-100)", digits=(5, 1))

    churn_risk = fields.Selection(
        [
            ("low", "Bajo"),
            ("medium", "Medio"),
            ("high", "Alto"),
        ],
        string="Riesgo de abandono",
    )
    churn_probability = fields.Float(
        string="P(churn) — modelo ML", digits=(5, 3),
        help="Probabilidad de baja calculada por ChurnProbabilityModel. Distinta de "
             "'Riesgo de abandono', que también se puede calcular con la "
             "regla manual de action_compute_score().",
    )
    expected_lifetime_months = fields.Float(
        string="Vida restante estimada (meses)", digits=(5, 1),
        help="Mediana de meses que se espera que el socio siga siendo socio, "
             "calculada por ChurnSurvivalModel. Vacío si todavía no hay "
             "ningún modelo de supervivencia entrenado.",
    )
    segment = fields.Selection(
        [
            ("new", "Nuevo"),
            ("loyal", "Fiel"),
            ("at_risk", "En riesgo"),
            ("inactive", "Inactivo"),
            ("churned", "Perdido"),
        ],
        string="Segmento",
    )
    notes = fields.Text(string="Notas")

    display_name = fields.Char(compute="_compute_display_name")

    @api.depends("partner_id", "date")
    def _compute_display_name(self):
        for rec in self:
            rec.display_name = f"{rec.partner_id.name} — {rec.date}"

    def get_latest_for_partner(self, partner):
        """Último Health Score calculado para ``partner`` (o un recordset
        vacío si todavía no se le ha calculado ninguno)."""
        return self.sudo().search(
            [("partner_id", "=", partner.id)], order="date desc", limit=1
        )

    def is_at_risk_for_promo(self, partner, threshold=0.5):
        """True si el modelo de churn (ML) le predice a ``partner`` una
        probabilidad de baja igual o superior a ``threshold``. Se usa para
        decidir si se le muestran promociones dirigidas a socios en
        riesgo (ver ``gym.promotion.at_risk_only``). Usa sudo() para poder
        consultar el Health Score aunque el socio del portal no tenga
        acceso directo a ``gym.customer.health``; no se expone el registro,
        solo el booleano resultante."""
        latest = self.get_latest_for_partner(partner)
        return bool(latest) and latest.churn_probability >= threshold

    def action_compute_score(self):
        today = date.today()
        for rec in self:
            logs = self.env["gym.access"].search(
                [("partner_id", "=", rec.partner_id.id)]
            )

            d30 = today - timedelta(days=30)
            d60 = today - timedelta(days=60)
            d90 = today - timedelta(days=90)

            visits_30 = logs.filtered(
                lambda l: l.check_in and l.check_in.date() >= d30
            )
            visits_60 = logs.filtered(
                lambda l: l.check_in and l.check_in.date() >= d60
            )
            visits_90 = logs.filtered(
                lambda l: l.check_in and l.check_in.date() >= d90
            )

            rec.visits_last_30_days = len(visits_30)
            rec.visits_last_60_days = len(visits_60)
            rec.visits_last_90_days = len(visits_90)

            if logs:
                last_visit = max(
                    l.check_in.date() for l in logs if l.check_in
                )
                rec.days_since_last_visit = (today - last_visit).days
            else:
                rec.days_since_last_visit = 999

            rec.avg_weekly_visits = rec.visits_last_30_days / 4.0
            rec.engagement_score = min(100.0, (rec.visits_last_30_days / 12.0) * 100)

            # Segment and churn risk logic
            if rec.days_since_last_visit > 60:
                rec.churn_risk = "high"
                rec.segment = "inactive" if rec.visits_last_90_days > 0 else "churned"
            elif rec.days_since_last_visit > 30:
                rec.churn_risk = "high"
                rec.segment = "at_risk"
            elif rec.visits_last_30_days >= 8:
                rec.churn_risk = "low"
                rec.segment = "loyal"
            elif rec.visits_last_30_days >= 4:
                rec.churn_risk = "medium"
                rec.segment = "at_risk"
            elif rec.visits_last_30_days >= 1:
                rec.churn_risk = "medium"
                rec.segment = "at_risk"
            else:
                rec.churn_risk = "high"
                rec.segment = "inactive"

            # New member override: if fewer than 30 days in the gym
            if rec.partner_id.membership_start and (
                today - rec.partner_id.membership_start
            ).days < 31:
                rec.segment = "new"
                rec.churn_risk = "low"

            rec.date = today

    def action_run_scoring_now(self):
        """Botón de la vista (lista/kanban): ejecuta el scoring de churn
        sobre todos los socios activos, igual que el cron diario pero al
        instante. Requiere que ya exista un modelo entrenado."""
        if not self.env["gym.churn.probability.model"].get_latest():
            raise UserError(
                "Todavía no hay ningún modelo de probabilidad de churn "
                "entrenado. Ve a 'Entrenar modelo de probabilidad de "
                "churn' primero."
            )
        self._cron_score_churn()
        return self.env["ir.actions.act_window"]._for_xml_id(
            "gym_backoffice.gym_customer_health_action"
        )

    def _predict_lifetime_months(self, partners):
        """Devuelve ``{partner_id: meses_de_vida_mediana_estimados}`` con el
        último ``ChurnSurvivalModel`` entrenado. La estimación de vida es
        opcional: si todavía no se ha entrenado ningún modelo de
        supervivencia, devuelve ``{}`` y no bloquea el scoring de
        probabilidad de churn."""
        latest = self.env["gym.churn.survival.model"].get_latest()
        if not latest:
            return {}

        tmp_path = os.path.join(
            tempfile.gettempdir(), f"churn_survival_model_cron_{latest.id}.joblib"
        )
        with open(tmp_path, "wb") as f:
            f.write(base64.b64decode(latest.model_file))
        try:
            model = ChurnSurvivalModel.load_model(tmp_path)
        finally:
            os.remove(tmp_path)

        X, _ = PartnerFeatureBuilder().build_survival(partners)
        months = model.predict(X)
        return {partner.id: float(m) for partner, m in zip(partners, months)}

    def _cron_score_churn(self):
        """Llamado por el cron diario (ver ``data/gym_churn_cron.xml``):
        puntúa con el último ``ChurnProbabilityModel`` entrenado a los
        socios que todavía no se han dado de baja, y guarda el resultado
        como nuevos registros de ``gym.customer.health``. Si además hay un
        ``ChurnSurvivalModel`` entrenado, cada registro incluye también la
        vida restante estimada (``expected_lifetime_months``)."""
        latest = self.env["gym.churn.probability.model"].get_latest()
        if not latest:
            _logger.warning(
                "gym.churn.trainer: no hay ningún modelo de probabilidad de "
                "churn entrenado todavía; se omite el scoring diario."
            )
            return

        partners = self.env["res.partner"].search([
            ("is_gym_member", "=", True),
            ("member_status", "!=", "churned"),
        ])
        if not partners:
            return

        tmp_path = os.path.join(
            tempfile.gettempdir(), f"churn_probability_model_cron_{latest.id}.joblib"
        )
        with open(tmp_path, "wb") as f:
            f.write(base64.b64decode(latest.model_file))
        try:
            model = ChurnProbabilityModel.load_model(tmp_path)
        finally:
            os.remove(tmp_path)

        X, _ = PartnerFeatureBuilder().build(partners)
        proba = model.predict_proba(X)[:, 1]
        lifetime_by_partner = self._predict_lifetime_months(partners)

        today = fields.Date.today()
        for partner, p in zip(partners, proba):
            churn_risk = "high" if p >= 0.60 else "medium" if p >= 0.30 else "low"
            self.create({
                "partner_id": partner.id,
                "date": today,
                "churn_probability": float(p),
                "churn_risk": churn_risk,
                "expected_lifetime_months": lifetime_by_partner.get(partner.id, 0.0),
            })

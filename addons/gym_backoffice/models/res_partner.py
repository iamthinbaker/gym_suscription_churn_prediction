from datetime import date, timedelta

from odoo import api, fields, models


class ResPartner(models.Model):
    _inherit = "res.partner"

    is_gym_member = fields.Boolean(string="Es socio del gimnasio")
    gym_center_id = fields.Many2one(
        "gym.center", string="Centro deportivo", tracking=True
    )
    membership_type = fields.Selection(
        [
            ("basic", "Básica"),
            ("premium", "Premium"),
            ("vip", "VIP"),
        ],
        string="Tipo de membresía",
        tracking=True,
    )
    membership_start = fields.Date(string="Fecha de alta")
    membership_end = fields.Date(string="Fecha de renovación")
    member_status = fields.Selection(
        [
            ("new", "Nuevo"),
            ("active", "Activo"),
            ("inactive", "Inactivo"),
            ("churned", "Dado de baja"),
        ],
        string="Estado",
        default="new",
        tracking=True,
    )

    access_log_ids = fields.One2many(
        "gym.access", "partner_id", string="Accesos"
    )
    engagement_ids = fields.One2many(
        "gym.engagement", "partner_id", string="Actividades"
    )
    health_score_ids = fields.One2many(
        "gym.customer.health", "partner_id", string="Health Scores"
    )

    access_log_count = fields.Integer(
        string="Accesos", compute="_compute_gym_stats"
    )
    engagement_count = fields.Integer(
        string="Actividades", compute="_compute_gym_stats"
    )
    health_score_count = fields.Integer(
        string="Health Scores", compute="_compute_gym_stats"
    )
    visits_last_30_days = fields.Integer(
        string="Visitas (30 días)", compute="_compute_gym_stats"
    )
    days_since_last_visit = fields.Integer(
        string="Días sin visitar", compute="_compute_gym_stats"
    )
    churn_risk = fields.Selection(
        [
            ("low", "Bajo"),
            ("medium", "Medio"),
            ("high", "Alto"),
        ],
        string="Riesgo de abandono",
        compute="_compute_gym_stats",
        store=True,
    )
    survival_prediction_months = fields.Float(
        string="Predicción de supervivencia (meses)",
        compute="_compute_survival_prediction",
        digits=(5, 1),
    )

    @api.depends("health_score_ids.expected_lifetime_months", "health_score_ids.date")
    def _compute_survival_prediction(self):
        for partner in self:
            last = partner.health_score_ids.sorted("date", reverse=True)[:1]
            partner.survival_prediction_months = (
                last.expected_lifetime_months if last else 0.0
            )

    @api.depends("access_log_ids", "engagement_ids", "health_score_ids")
    def _compute_gym_stats(self):
        today = date.today()
        d30 = today - timedelta(days=30)
        for partner in self:
            partner.access_log_count = len(partner.access_log_ids)
            partner.engagement_count = len(partner.engagement_ids)
            partner.health_score_count = len(partner.health_score_ids)

            recent = partner.access_log_ids.filtered(
                lambda l: l.check_in and l.check_in.date() >= d30
            )
            partner.visits_last_30_days = len(recent)

            if partner.access_log_ids:
                last = max(
                    l.check_in.date()
                    for l in partner.access_log_ids
                    if l.check_in
                )
                partner.days_since_last_visit = (today - last).days
            else:
                partner.days_since_last_visit = 999

            v = partner.visits_last_30_days
            d = partner.days_since_last_visit
            if d > 30 or v == 0:
                partner.churn_risk = "high"
            elif v >= 8:
                partner.churn_risk = "low"
            else:
                partner.churn_risk = "medium"

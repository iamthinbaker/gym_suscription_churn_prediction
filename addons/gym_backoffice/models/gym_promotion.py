from odoo import fields, models


class GymPromotion(models.Model):
    _name = "gym.promotion"
    _description = "Promoción"
    _order = "date_start desc"

    gym_center_id = fields.Many2one(
        "gym.center",
        string="Centro",
        help="Déjalo vacío para que la promoción aplique a todos los centros.",
    )

    name = fields.Char(string="Título", required=True)
    description = fields.Text(string="Descripción")
    date_start = fields.Date(string="Fecha de inicio")
    date_end = fields.Date(string="Fecha de fin")
    active = fields.Boolean(default=True)

    at_risk_only = fields.Boolean(
        string="Solo socios en riesgo de baja",
        help="Si se marca, esta promoción solo se muestra en la app a los "
             "socios a los que el modelo de churn les predice una "
             "probabilidad de baja alta. Déjalo desmarcado para que la "
             "vean todos los socios.",
    )

from odoo import fields, models


class GymChurnSurvivalFeatureImportance(models.Model):
    _name = "gym.churn.survival.feature.importance"
    _description = "Coeficiente de una feature en un modelo de supervivencia entrenado"

    churn_survival_model_id = fields.Many2one(
        "gym.churn.survival.model",
        string="Modelo de supervivencia",
        required=True,
        ondelete="cascade",
    )
    name = fields.Char(string="Feature", required=True)
    importance = fields.Float(
        string="Coeficiente",
        digits=(6, 4),
        help="Coeficiente del parámetro de escala (alpha_) del modelo AFT. "
             "Negativo = acorta la vida del socio, positivo = la alarga.",
    )

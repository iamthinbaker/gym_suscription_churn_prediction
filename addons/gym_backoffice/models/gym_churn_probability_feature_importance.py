from odoo import fields, models


class GymChurnProbabilityFeatureImportance(models.Model):
    _name = "gym.churn.probability.feature.importance"
    _description = "Importancia de una feature en un modelo de probabilidad de churn entrenado"
    _order = "importance desc"

    churn_probability_model_id = fields.Many2one(
        "gym.churn.probability.model",
        string="Modelo de probabilidad de churn",
        required=True,
        ondelete="cascade",
    )
    name = fields.Char(string="Feature", required=True)
    importance = fields.Float(string="Importancia", digits=(6, 4))
    importance_pct = fields.Float(
        string="% importancia", compute="_compute_importance_pct"
    )

    def _compute_importance_pct(self):
        for rec in self:
            rec.importance_pct = rec.importance * 100

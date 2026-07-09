from odoo import fields, models


class GymChurnFeatureImportance(models.Model):
    _name = "gym.churn.feature.importance"
    _description = "Importancia de una feature en un modelo de churn entrenado"
    _order = "importance desc"

    churn_model_id = fields.Many2one(
        "gym.churn.model", string="Modelo de churn", required=True, ondelete="cascade"
    )
    name = fields.Char(string="Feature", required=True)
    importance = fields.Float(string="Importancia", digits=(6, 4))
    importance_pct = fields.Float(
        string="% importancia", compute="_compute_importance_pct"
    )

    def _compute_importance_pct(self):
        for rec in self:
            rec.importance_pct = rec.importance * 100

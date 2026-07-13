from odoo import fields, models


class GymChurnProbabilityModel(models.Model):
    _name = "gym.churn.probability.model"
    _description = "Modelo de probabilidad de churn entrenado (histórico persistente)"
    _order = "trained_at desc"
    _rec_name = "trained_at"

    trained_at = fields.Datetime(string="Entrenado el", required=True)
    n_customers = fields.Integer(string="Socios usados para entrenar")
    n_churned = fields.Integer(string="Bajas en el histórico")
    churn_rate = fields.Float(string="Tasa de churn", digits=(5, 3))
    model_file = fields.Binary(string="Modelo entrenado (.joblib)", required=True, attachment=True)
    model_filename = fields.Char(default="churn_probability_model.joblib")
    feature_importance_ids = fields.One2many(
        "gym.churn.probability.feature.importance",
        "churn_probability_model_id",
        string="Importancia de features",
    )

    def get_latest(self):
        """Devuelve el registro del modelo entrenado más reciente (o un
        recordset vacío si todavía no se ha entrenado ninguno)."""
        return self.search([], order="trained_at desc", limit=1)

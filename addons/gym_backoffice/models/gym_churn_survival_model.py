from odoo import fields, models


class GymChurnSurvivalModel(models.Model):
    _name = "gym.churn.survival.model"
    _description = "Modelo de supervivencia (tiempo de vida) entrenado (histórico persistente)"
    _order = "trained_at desc"
    _rec_name = "trained_at"

    trained_at = fields.Datetime(string="Entrenado el", required=True)
    n_customers = fields.Integer(string="Socios usados para entrenar")
    n_events = fields.Integer(string="Bajas observadas en el histórico")
    event_rate = fields.Float(string="Tasa de bajas observadas", digits=(5, 3))
    model_file = fields.Binary(string="Modelo entrenado (.joblib)", required=True, attachment=True)
    model_filename = fields.Char(default="churn_survival_model.joblib")
    feature_importance_ids = fields.One2many(
        "gym.churn.survival.feature.importance",
        "churn_survival_model_id",
        string="Coeficientes del modelo",
    )

    def get_latest(self):
        """Devuelve el registro del modelo entrenado más reciente (o un
        recordset vacío si todavía no se ha entrenado ninguno)."""
        return self.search([], order="trained_at desc", limit=1)

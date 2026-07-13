"""
Wizard de entrenamiento del modelo de supervivencia (tiempo de vida) de churn.

Responsabilidades (en este orden):
  1. Leer los datos de los distintos módulos de Odoo (``res.partner`` y sus
     relaciones ``gym.access`` / ``gym.engagement``).
  2. Feature engineering
     (``engine.odoo_features.PartnerFeatureBuilder.build_survival``).
  3. Entrenar ``ChurnSurvivalModel`` y guardarlo — tanto en el propio
     wizard (para descarga inmediata) como en ``gym.churn.survival.model``
     (registro persistente que usa el cron diario de scoring, ver
     ``models/gym_customer_health.py``).
"""

import base64
import os
import tempfile

from odoo import fields, models

from ..engine.churn_survival_model import ChurnSurvivalModel
from ..engine.odoo_features import PartnerFeatureBuilder


class GymChurnSurvivalTrainer(models.TransientModel):
    _name = "gym.churn.survival.trainer"
    _description = "Entrenador del modelo de supervivencia (tiempo de vida) de churn"

    trained_at = fields.Datetime(string="Entrenado el", readonly=True)
    n_customers = fields.Integer(string="Socios usados para entrenar", readonly=True)
    n_events = fields.Integer(string="Bajas observadas en el histórico", readonly=True)
    event_rate = fields.Float(
        string="Tasa de bajas observadas", readonly=True, digits=(5, 3)
    )
    model_file = fields.Binary(string="Modelo entrenado (.joblib)", readonly=True)
    model_filename = fields.Char(
        default="churn_survival_model.joblib", readonly=True
    )
    churn_survival_model_id = fields.Many2one(
        "gym.churn.survival.model",
        string="Modelo de supervivencia persistido",
        readonly=True,
    )
    feature_importance_ids = fields.One2many(
        related="churn_survival_model_id.feature_importance_ids",
        string="Coeficientes del modelo",
    )

    def _fetch_partners(self):
        return self.env["res.partner"].search([("is_gym_member", "=", True)])

    def _train(self):
        """Entrena el modelo y lo persiste. Devuelve (X, y) por si el
        llamante quiere encadenar un scoring inmediato."""
        partners = self._fetch_partners()
        X, y = PartnerFeatureBuilder().build_survival(partners)

        model = ChurnSurvivalModel()
        model.fit(X, y)
        importances = model.get_feature_importances()

        tmp_path = os.path.join(
            tempfile.gettempdir(), f"churn_survival_model_{self.id}.joblib"
        )
        model.save_model(tmp_path)
        with open(tmp_path, "rb") as f:
            model_bytes = f.read()
        os.remove(tmp_path)
        model_b64 = base64.b64encode(model_bytes)

        feature_importance_cmds = [
            (0, 0, {"name": name, "importance": importance})
            for name, importance in importances
        ]

        n_events = int(y["event"].sum())
        event_rate = float(y["event"].mean()) if len(y) else 0.0

        # Registro persistente: el cron diario de scoring lee de aquí.
        churn_survival_model = self.env["gym.churn.survival.model"].create({
            "trained_at": fields.Datetime.now(),
            "n_customers": len(X),
            "n_events": n_events,
            "event_rate": event_rate,
            "model_file": model_b64,
            "model_filename": "churn_survival_model.joblib",
            "feature_importance_ids": feature_importance_cmds,
        })

        self.write({
            "trained_at": fields.Datetime.now(),
            "n_customers": len(X),
            "n_events": n_events,
            "event_rate": event_rate,
            "model_file": model_b64,
            "model_filename": "churn_survival_model.joblib",
            "churn_survival_model_id": churn_survival_model.id,
        })

        return X, y

    def action_train_model(self):
        self.ensure_one()
        self._train()
        return {
            "type": "ir.actions.act_window",
            "res_model": self._name,
            "res_id": self.id,
            "view_mode": "form",
            "target": "new",
        }

    def action_train_and_score(self):
        """Igual que ``action_train_model``, pero además ejecuta el
        scoring inmediatamente (sin esperar al cron diario de medianoche)."""
        self.ensure_one()
        self._train()
        self.env["gym.customer.health"]._cron_score_churn()
        return {
            "type": "ir.actions.act_window",
            "res_model": self._name,
            "res_id": self.id,
            "view_mode": "form",
            "target": "new",
        }

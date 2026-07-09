"""
Wizard de entrenamiento del modelo de churn.

Responsabilidades (en este orden):
  1. Leer los datos de los distintos módulos de Odoo (``res.partner`` y sus
     relaciones ``gym.access`` / ``gym.engagement``).
  2. Feature engineering (``engine.odoo_features.PartnerFeatureBuilder``).
  3. Entrenar ``ChurnModel`` y guardarlo — tanto en el propio wizard (para
     descarga inmediata) como en ``gym.churn.model`` (registro persistente
     que usa el cron diario de scoring, ver ``models/gym_customer_health.py``).
"""

import base64
import os
import tempfile

from odoo import fields, models

from ..engine.churn_model import ChurnModel
from ..engine.odoo_features import PartnerFeatureBuilder


class GymChurnTrainer(models.TransientModel):
    _name = "gym.churn.trainer"
    _description = "Entrenador del modelo de predicción de churn"

    trained_at = fields.Datetime(string="Entrenado el", readonly=True)
    n_customers = fields.Integer(string="Socios usados para entrenar", readonly=True)
    n_churned = fields.Integer(string="Bajas en el histórico", readonly=True)
    churn_rate = fields.Float(string="Tasa de churn", readonly=True, digits=(5, 3))
    model_file = fields.Binary(string="Modelo entrenado (.joblib)", readonly=True)
    model_filename = fields.Char(default="churn_model.joblib", readonly=True)

    def _fetch_partners(self):
        return self.env["res.partner"].search([("is_gym_member", "=", True)])

    def _train(self):
        """Entrena el modelo y lo persiste. Devuelve (X, y) por si el
        llamante quiere encadenar un scoring inmediato."""
        partners = self._fetch_partners()
        X, y = PartnerFeatureBuilder().build(partners)

        model = ChurnModel()
        model.fit(X, y)

        tmp_path = os.path.join(tempfile.gettempdir(), f"churn_model_{self.id}.joblib")
        model.save_model(tmp_path)
        with open(tmp_path, "rb") as f:
            model_bytes = f.read()
        os.remove(tmp_path)
        model_b64 = base64.b64encode(model_bytes)

        self.write({
            "trained_at": fields.Datetime.now(),
            "n_customers": len(X),
            "n_churned": int(y.sum()),
            "churn_rate": float(y.mean()) if len(y) else 0.0,
            "model_file": model_b64,
            "model_filename": "churn_model.joblib",
        })

        # Registro persistente: el cron diario de scoring lee de aquí.
        self.env["gym.churn.model"].create({
            "trained_at": fields.Datetime.now(),
            "n_customers": len(X),
            "n_churned": int(y.sum()),
            "churn_rate": float(y.mean()) if len(y) else 0.0,
            "model_file": model_b64,
            "model_filename": "churn_model.joblib",
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

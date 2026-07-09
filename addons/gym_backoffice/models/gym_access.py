from odoo import api, fields, models


class GymAccess(models.Model):
    _name = "gym.access"
    _description = "Registro de Acceso"
    _order = "check_in desc"

    partner_id = fields.Many2one(
        "res.partner",
        string="Socio",
        required=True,
        domain=[("is_gym_member", "=", True)],
    )
    gym_center_id = fields.Many2one("gym.center", string="Centro")
    check_in = fields.Datetime(
        string="Entrada", required=True, default=fields.Datetime.now
    )
    check_out = fields.Datetime(string="Salida")
    duration = fields.Float(
        string="Duración (h)", compute="_compute_duration", store=True
    )
    activity_type = fields.Selection(
        [
            ("gym_floor", "Sala de musculación"),
            ("cardio", "Cardio"),
            ("pool", "Piscina"),
            ("class", "Clase grupal"),
            ("personal_training", "Entrenamiento personal"),
        ],
        string="Actividad",
    )

    @api.depends("check_in", "check_out")
    def _compute_duration(self):
        for record in self:
            if record.check_in and record.check_out:
                delta = record.check_out - record.check_in
                record.duration = delta.total_seconds() / 3600
            else:
                record.duration = 0.0

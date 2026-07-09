from odoo import fields, models


class GymEngagement(models.Model):
    _name = "gym.engagement"
    _description = "Participación en Actividad"
    _order = "date desc"

    partner_id = fields.Many2one(
        "res.partner",
        string="Socio",
        required=True,
        domain=[("is_gym_member", "=", True)],
    )
    gym_center_id = fields.Many2one("gym.center", string="Centro")
    date = fields.Date(string="Fecha", required=True, default=fields.Date.today)
    activity_type = fields.Selection(
        [
            ("yoga", "Yoga"),
            ("spinning", "Spinning"),
            ("pilates", "Pilates"),
            ("personal_training", "Entrenamiento Personal"),
            ("group_class", "Clase Grupal"),
            ("zumba", "Zumba"),
            ("crossfit", "CrossFit"),
            ("aquagym", "Aquagym"),
        ],
        string="Tipo de actividad",
        required=True,
    )
    rating = fields.Selection(
        [
            ("1", "⭐ Muy malo"),
            ("2", "⭐⭐ Malo"),
            ("3", "⭐⭐⭐ Regular"),
            ("4", "⭐⭐⭐⭐ Bueno"),
            ("5", "⭐⭐⭐⭐⭐ Excelente"),
        ],
        string="Valoración",
    )
    notes = fields.Text(string="Notas")

from odoo import api, fields, models


class GymClass(models.Model):
    _name = "gym.class"
    _description = "Clase de GymBaker"
    _order = "date_start"
    _rec_name = "name"

    gym_center_id = fields.Many2one(
        "gym.center", string="Centro", required=True
    )
    booking_ids = fields.One2many(
        "gym.class.booking", "class_id", string="Reservas"
    )

    name = fields.Char(string="Nombre", required=True)
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
    trainer_name = fields.Char(string="Entrenador")
    date_start = fields.Datetime(string="Fecha y hora", required=True)
    duration = fields.Float(string="Duración (h)", default=1.0)
    capacity = fields.Integer(string="Aforo", default=20)
    active = fields.Boolean(default=True)

    seats_taken = fields.Integer(
        string="Plazas ocupadas", compute="_compute_seats"
    )
    seats_available = fields.Integer(
        string="Plazas libres", compute="_compute_seats"
    )

    @api.depends("booking_ids.state", "capacity")
    def _compute_seats(self):
        for record in self:
            taken = len(
                record.booking_ids.filtered(lambda b: b.state == "confirmed")
            )
            record.seats_taken = taken
            record.seats_available = max(record.capacity - taken, 0)

    def _has_available_seats(self):
        self.ensure_one()
        return self.seats_available > 0

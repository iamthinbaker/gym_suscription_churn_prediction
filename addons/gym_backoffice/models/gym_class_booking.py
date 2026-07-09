from odoo import api, fields, models
from odoo.exceptions import ValidationError


class GymClassBooking(models.Model):
    _name = "gym.class.booking"
    _description = "Reserva de Clase"
    _order = "booking_date desc"

    class_id = fields.Many2one(
        "gym.class", string="Clase", required=True, ondelete="cascade"
    )
    partner_id = fields.Many2one(
        "res.partner",
        string="Socio",
        required=True,
        domain=[("is_gym_member", "=", True)],
    )
    gym_center_id = fields.Many2one(
        "gym.center",
        string="Centro",
        related="class_id.gym_center_id",
        store=True,
    )

    state = fields.Selection(
        [
            ("confirmed", "Confirmada"),
            ("cancelled", "Cancelada"),
        ],
        string="Estado",
        default="confirmed",
        required=True,
    )
    booking_date = fields.Datetime(
        string="Fecha de reserva", default=fields.Datetime.now
    )

    @api.constrains("state", "class_id", "partner_id")
    def _check_no_duplicate(self):
        for record in self:
            if record.state != "confirmed":
                continue
            duplicate = self.search_count(
                [
                    ("id", "!=", record.id),
                    ("class_id", "=", record.class_id.id),
                    ("partner_id", "=", record.partner_id.id),
                    ("state", "=", "confirmed"),
                ]
            )
            if duplicate:
                raise ValidationError(
                    "El socio ya tiene una reserva confirmada para esta clase."
                )

    @api.constrains("state", "class_id")
    def _check_capacity(self):
        for record in self.mapped("class_id"):
            confirmed = self.search_count(
                [("class_id", "=", record.id), ("state", "=", "confirmed")]
            )
            if confirmed > record.capacity:
                raise ValidationError(
                    f"No quedan plazas libres en la clase «{record.name}»."
                )

    def action_cancel(self):
        self.write({"state": "cancelled"})

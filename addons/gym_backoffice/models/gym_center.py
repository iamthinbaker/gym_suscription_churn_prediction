from odoo import fields, models


class GymCenter(models.Model):
    _name = "gym.center"
    _description = "Centro Deportivo"
    _rec_name = "name"

    name = fields.Char(string="Nombre", required=True)
    street = fields.Char(string="Dirección")
    city = fields.Char(string="Ciudad")
    phone = fields.Char(string="Teléfono")
    email = fields.Char(string="Email")
    capacity = fields.Integer(string="Aforo máximo")
    active = fields.Boolean(default=True)

    member_ids = fields.One2many(
        "res.partner",
        "gym_center_id",
        string="Socios",
        domain=[("is_gym_member", "=", True)],
    )
    member_count = fields.Integer(
        string="Socios", compute="_compute_member_count"
    )
    access_log_count = fields.Integer(
        string="Accesos", compute="_compute_access_log_count"
    )

    def _compute_member_count(self):
        for center in self:
            center.member_count = len(center.member_ids)

    def _compute_access_log_count(self):
        GymAccess = self.env["gym.access"]
        for center in self:
            center.access_log_count = GymAccess.search_count(
                [("gym_center_id", "=", center.id)]
            )

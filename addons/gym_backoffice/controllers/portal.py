from odoo import fields, http
from odoo.addons.portal.controllers.portal import CustomerPortal
from odoo.exceptions import AccessError, MissingError, ValidationError
from odoo.http import request


class GymPortal(CustomerPortal):

    @http.route("/my/gym", type="http", auth="user", website=True)
    def gym_dashboard(self, **kw):
        partner = request.env.user.partner_id
        values = {
            "partner": partner,
            "center": partner.gym_center_id,
            "booking_count": request.env["gym.class.booking"].search_count(
                [("partner_id", "=", partner.id), ("state", "=", "confirmed")]
            ),
            "class_count": request.env["gym.class"].search_count(
                [("date_start", ">=", fields.Datetime.now())]
            ),
            "promotions": request.env["gym.promotion"].search(
                [], order="date_start desc"
            ),
        }
        return request.render("gym_backoffice.portal_my_gym", values)

    @http.route("/my/gym/classes", type="http", auth="user", website=True)
    def gym_classes(self, msg=None, err=None, **kw):
        partner = request.env.user.partner_id
        classes = request.env["gym.class"].search(
            [("date_start", ">=", fields.Datetime.now())],
            order="date_start",
        )
        values = {
            "partner": partner,
            "classes": classes,
            "msg": msg,
            "err": err,
        }
        return request.render("gym_backoffice.portal_gym_classes", values)

    @http.route(
        "/my/gym/classes/<model('gym.class'):gym_class>/book",
        type="http",
        auth="user",
        website=True,
        methods=["POST"],
    )
    def gym_class_book(self, gym_class, **kw):
        partner = request.env.user.partner_id
        try:
            if gym_class.gym_center_id != partner.gym_center_id:
                raise AccessError("No puedes reservar clases de otro centro.")
            if not gym_class._has_available_seats():
                return request.redirect("/my/gym/classes?err=full")
            request.env["gym.class.booking"].create(
                {"class_id": gym_class.id, "partner_id": partner.id}
            )
        except (AccessError, MissingError):
            return request.redirect("/my")
        except ValidationError:
            return request.redirect("/my/gym/classes?err=dup")
        return request.redirect("/my/gym/classes?msg=booked")

    @http.route("/my/gym/bookings", type="http", auth="user", website=True)
    def gym_bookings(self, msg=None, err=None, **kw):
        partner = request.env.user.partner_id
        bookings = request.env["gym.class.booking"].search(
            [("partner_id", "=", partner.id)], order="booking_date desc"
        )
        values = {
            "partner": partner,
            "bookings": bookings,
            "msg": msg,
            "err": err,
        }
        return request.render("gym_backoffice.portal_gym_bookings", values)

    @http.route(
        "/my/gym/bookings/<model('gym.class.booking'):booking>/cancel",
        type="http",
        auth="user",
        website=True,
        methods=["POST"],
    )
    def gym_booking_cancel(self, booking, **kw):
        partner = request.env.user.partner_id
        try:
            if booking.partner_id != partner:
                raise AccessError("Esta reserva no pertenece al socio.")
            booking.action_cancel()
        except (AccessError, MissingError):
            return request.redirect("/my")
        return request.redirect("/my/gym/bookings?msg=cancelled")

    @http.route("/my/gym/promotions", type="http", auth="user", website=True)
    def gym_promotions(self, **kw):
        partner = request.env.user.partner_id
        promotions = request.env["gym.promotion"].search(
            [], order="date_start desc"
        )
        values = {
            "partner": partner,
            "promotions": promotions,
        }
        return request.render("gym_backoffice.portal_gym_promotions", values)

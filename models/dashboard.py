from odoo import models, fields, api


class EventCateringDashboard(models.Model):
    _name = "event.catering.dashboard"
    _description = "Event Catering Dashboard"

    name = fields.Char(default="Tableau de bord")

    total_events = fields.Integer(
        string="Total événements",
        compute="_compute_statistics"
    )

    confirmed_events = fields.Integer(
        string="Confirmés",
        compute="_compute_statistics"
    )

    running_events = fields.Integer(
        string="En cours",
        compute="_compute_statistics"
    )

    done_events = fields.Integer(
        string="Terminés",
        compute="_compute_statistics"
    )

    @api.depends()
    def _compute_statistics(self):
        Event = self.env["event.catering.event"]

        for dashboard in self:
            dashboard.total_events = Event.search_count([])

            dashboard.confirmed_events = Event.search_count([
                ("state", "=", "confirmed")
            ])

            dashboard.running_events = Event.search_count([
                ("state", "=", "in_progress")
            ])

            dashboard.done_events = Event.search_count([
                ("state", "=", "done")
            ])
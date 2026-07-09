from collections import Counter

from odoo import api, models


class EventCateringDashboard(models.Model):
    _name = "event.catering.dashboard"
    _description = "Event Catering Dashboard"

    @api.model
    def get_dashboard_data(self):

        events = self.env["event.catering.event"].sudo().search([])

        # =====================
        # KPI
        # =====================

        total_events = len(events)
        total_guests = 0
        estimated_budget = 0
        actual_budget = 0

        # =====================
        # Statistiques
        # =====================

        states = Counter()
        event_types = Counter()
        months = Counter()
        guests_by_type = Counter()
        budget_by_type = {}

        for event in events:

            # KPI
            total_guests += event.guests_count or 0
            estimated_budget += event.budget_estimated or 0
            actual_budget += event.budget_difference or 0

            # États
            states[event.state] += 1

            # Types
            if event.event_type_id:

                type_name = event.event_type_id.name

                event_types[type_name] += 1

                guests_by_type[type_name] += event.guests_count or 0

                if type_name not in budget_by_type:
                    budget_by_type[type_name] = {
                        "estimated": 0,
                        "actual": 0,
                    }

                budget_by_type[type_name]["estimated"] += (
                    event.budget_estimated or 0
                )

                budget_by_type[type_name]["actual"] += (
                    event.budget_actual or 0
                )

            # Évolution mensuelle
            if event.date_start:
                month = event.date_start.strftime("%Y-%m")
                months[month] += 1

        return {

            # KPI
            "kpi": {
                "events": total_events,
                "guests": total_guests,
                "estimated_budget": estimated_budget,
                "actual_budget": actual_budget,
            },

            # Doughnut
            "states": {
                "labels": list(states.keys()),
                "values": list(states.values()),
            },

            # Bar chart
            "types": {
                "labels": list(event_types.keys()),
                "values": list(event_types.values()),
            },

            # Line chart
            "months": {
                "labels": list(months.keys()),
                "values": list(months.values()),
            },

            # Budget
            "budget": {
                "labels": list(budget_by_type.keys()),
                "estimated": [
                    value["estimated"]
                    for value in budget_by_type.values()
                ],
                "actual": [
                    value["actual"]
                    for value in budget_by_type.values()
                ],
            },

            # Invités
            "guests": {
                "labels": list(guests_by_type.keys()),
                "values": list(guests_by_type.values()),
            },
        }
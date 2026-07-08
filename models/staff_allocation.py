from odoo import models, fields

class EventCateringStaffAllocation(models.Model):
    _name = 'event.catering.staff.allocation'
    _description = 'Staff Allocation for Event'
    
    event_id = fields.Many2one('event.catering.event', string='Event', required=True, ondelete='cascade')
    employee_id = fields.Many2one('hr.employee', string='Employee', required=True)
    role = fields.Char(string='Role')
    start_time = fields.Datetime(string='Start Time')
    end_time = fields.Datetime(string='End Time')
    notes = fields.Text(string='Notes')
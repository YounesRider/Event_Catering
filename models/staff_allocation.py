from odoo import models, fields

class EventCateringStaffAllocation(models.Model):
    _name = 'event.catering.staff.allocation'
    _description = 'Staff Allocation for Event'
    
    event_id = fields.Many2one('event.catering.event', string='Event', required=True, ondelete='cascade')
    employee_id = fields.Many2one('hr.employee', string='Employee', required=True)
    role = fields.Char(string='Role')
    # event.catering.staff.allocation
    certificate = fields.Selection(
    related='employee_id.certificate',
    store=True,
    readonly=True,
    )
    image_staff = fields.Image(
        string='Photo',
        related='employee_id.image_1920',
        readonly=True,
        store=False
    )
    notes = fields.Text(string='Notes')
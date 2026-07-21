from odoo import models, fields, api

class EventCateringEventLine(models.Model):
    _name = 'event.catering.event.line'
    _description = 'Event Line Item'
    
    event_id = fields.Many2one('event.catering.event', string='Event', required=True, ondelete='cascade')
    product_id = fields.Many2one('product.product', string='Product', required=True)
    quantity = fields.Float(string='Quantity', required=True, default=1.0)
    product_image=fields.Image(string='image')
    unit_price = fields.Float(string='Unit Price', related='product_id.list_price', readonly=True)
    total_price = fields.Float(string='Total Price', compute='_compute_total_price', store=True)
    notes = fields.Text(string='Notes')
    
    @api.depends('quantity', 'unit_price')
    def _compute_total_price(self):
        for record in self:
            record.total_price = record.quantity * record.unit_price
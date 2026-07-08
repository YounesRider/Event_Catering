from odoo import models, fields

class EventCateringType(models.Model):
    _name = 'event.catering.type'
    _description = 'Event Type'
    
    name = fields.Char(string='Name', required=True)
    description = fields.Text(string='Description')
    color = fields.Integer(string='Color')
    staff_ratio = fields.Float(string='Staff Ratio', default=10.0,
                              help='Nombre d\'invités par membre du personnel')
    preparation_time = fields.Float(string='Preparation Time (hours)',
                                  help='Temps de préparation estimé en heures')
    active = fields.Boolean(string='Active', default=True)
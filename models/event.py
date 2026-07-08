from odoo import models, fields, api, _
from odoo.exceptions import ValidationError, UserError
from datetime import datetime, timedelta

class EventCateringEvent(models.Model):
    _name = 'event.catering.event'
    _description = 'Event for Catering'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'date_start desc'
    
    # Séquence pour la référence automatique
    @api.depends('name')
    def _compute_reference(self):
        for record in self:
            if not record.reference:
                seq = self.env['ir.sequence'].next_by_code('event.catering.event')
                record.reference = seq or 'EVENT/0001'
    
    # Champs
    name = fields.Char(string='Event Name', required=True, tracking=True)
    reference = fields.Char(string='Reference', compute='_compute_reference', store=True)
    client_id = fields.Many2one('res.partner', string='Client', required=True, tracking=True)
    event_type_id = fields.Many2one('event.catering.type', string='Event Type', required=True)
    date_start = fields.Datetime(string='Start Date', required=True, tracking=True)
    date_end = fields.Datetime(string='End Date', required=True, tracking=True)
    location = fields.Char(string='Location')
    city = fields.Char(string='City')
    room = fields.Char(string='Room')
    responsible_id = fields.Many2one('hr.employee', string='Responsible', tracking=True)
    guests_count = fields.Integer(string='Number of Guests', required=True, default=0)
    state = fields.Selection([
        ('draft', 'Draft'),
        ('quotation', 'Quotation'),
        ('confirmed', 'Confirmed'),
        ('preparation', 'Preparation'),
        ('in_progress', 'In Progress'),
        ('done', 'Done'),
        ('archived', 'Archived')
    ], string='Status', default='draft', tracking=True)
    notes = fields.Text(string='Notes')
    budget_estimated = fields.Float(string='Estimated Budget')
    budget_actual = fields.Float(string='Actual Budget')
    company_id = fields.Many2one('res.company', string='Company', default=lambda self: self.env.company)
    
    # Relations
    event_line_ids = fields.One2many('event.catering.event.line', 'event_id', string='Services')
    staff_allocation_ids = fields.One2many('event.catering.staff.allocation', 'event_id', string='Staff')
    
    # Champs calculés
    total_cost = fields.Float(string='Total Cost', compute='_compute_total_cost', store=True)
    recommended_staff = fields.Integer(string='Recommended Staff', compute='_compute_recommended_staff')
    
    @api.depends('event_line_ids.total_price')
    def _compute_total_cost(self):
        for record in self:
            record.total_cost = sum(record.event_line_ids.mapped('total_price'))
    
    @api.depends('guests_count', 'event_type_id')
    def _compute_recommended_staff(self):
        for record in self:
            if record.event_type_id and record.guests_count > 0:
                ratio = record.event_type_id.staff_ratio or 10.0
                record.recommended_staff = max(1, int(record.guests_count / ratio))
            else:
                record.recommended_staff = 0
    
    # Méthodes métier
    def action_confirm(self):
        self.ensure_one()
        # Vérification de disponibilité
        self._check_availability()
        # Vérification des conflits
        self._check_conflicts()
        # Changement d'état
        self.state = 'confirmed'
        # Réservation des produits
        self._reserve_products()
        # Envoi de notification
        self._notify_responsible()
        # Génération de devis
        self._generate_quotation()
    
    def action_prepare(self):
        self.ensure_one()
        self.state = 'preparation'
    
    def action_start(self):
        self.ensure_one()
        self.state = 'in_progress'
    
    def action_done(self):
        self.ensure_one()
        self.state = 'done'
    
    def action_archive(self):
        self.ensure_one()
        self.state = 'archived'
    
    def action_reset_to_draft(self):
        self.ensure_one()
        self.state = 'draft'
    
    def _check_availability(self):
        # Vérification des stocks
        for line in self.event_line_ids:
            product = line.product_id
            if product.type == 'product' and product.qty_available < line.quantity:
                raise ValidationError(
                    _("Stock insuffisant pour le produit %s. Disponible: %s, Requis: %s") %
                    (product.name, product.qty_available, line.quantity)
                )
    
    def _check_conflicts(self):
        # Vérification des conflits de planning
        domain = [
            ('id', '!=', self.id),
            ('date_start', '<', self.date_end),
            ('date_end', '>', self.date_start),
            ('state', 'in', ['confirmed', 'preparation', 'in_progress'])
        ]
        if self.responsible_id:
            domain.append(('responsible_id', '=', self.responsible_id.id))
        if self.room:
            domain.append(('room', '=', self.room))
        conflicting = self.search(domain)
        if conflicting:
            raise ValidationError(
                _("Conflit détecté avec l'événement : %s") %
                ', '.join(conflicting.mapped('name'))
            )
    
    def _reserve_products(self):
        # Logique de réservation des produits
        for line in self.event_line_ids:
            product = line.product_id
            if product.type == 'product':
                # Créer une réservation dans le stock
                self.env['stock.quant']._update_available_quantity(
                    product, product.product_tmpl_id.categ_id.property_stock_location,
                    -line.quantity
                )
    
    def _notify_responsible(self):
        if self.responsible_id:
            self.message_post(
                body=_("L'événement %s a été confirmé. Veuillez préparer les ressources nécessaires.") %
                self.name,
                partner_ids=[self.responsible_id.user_id.partner_id.id]
            )
    
    def _generate_quotation(self):
        # Génération d'un devis automatique
        sale_order = self.env['sale.order'].create({
            'partner_id': self.client_id.id,
            'user_id': self.responsible_id.user_id.id if self.responsible_id else self.env.user.id,
            'date_order': fields.Datetime.now(),
            'note': f"Devis pour l'événement: {self.name}",
            'company_id': self.company_id.id,
        })
        
        for line in self.event_line_ids:
            self.env['sale.order.line'].create({
                'order_id': sale_order.id,
                'product_id': line.product_id.id,
                'product_uom_qty': line.quantity,
                'price_unit': line.unit_price,
                'name': line.product_id.name,
            })
        
        return sale_order
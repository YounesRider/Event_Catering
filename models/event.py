from odoo import models, fields, api, _
from odoo.exceptions import ValidationError, UserError


class EventCateringEvent(models.Model):

    _name = 'event.catering.event'
    _description = 'Event for Catering'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'date_start desc'


    # ==================================================
    # Référence automatique
    # ==================================================

    @api.depends('name')
    def _compute_reference(self):

        for record in self:

            if not record.reference:

                seq = self.env['ir.sequence'].next_by_code(
                    'event.catering.event'
                )

                record.reference = seq or 'EVENT/0001'


    # ==================================================
    # Champs principaux
    # ==================================================

    name = fields.Char(
        string='Nom événement',
        required=True,
        tracking=True
    )


    reference = fields.Char(
        string='Référence',
        compute='_compute_reference',
        store=True
    )


    client_id = fields.Many2one(
        'res.partner',
        string='Client',
        required=True,
        tracking=True
    )


    event_type_id = fields.Many2one(
        'event.catering.type',
        string='Type événement',
        required=True
    )


    date_start = fields.Datetime(
        string='Début',
        required=True,
        tracking=True
    )


    date_end = fields.Datetime(
        string='Fin',
        required=True,
        tracking=True
    )


    location = fields.Char(
        string='Lieu'
    )


    city = fields.Char(
        string='Ville'
    )


    room = fields.Char(
        string='Salle'
    )


    responsible_id = fields.Many2one(
        'hr.employee',
        string='Responsable',
        tracking=True
    )


    guests_count = fields.Integer(
        string='Nombre invités',
        required=True,
        default=0
    )

    currency_id = fields.Many2one(
    'res.currency',
    string='Currency',
    related='company_id.currency_id',
    readonly=True
)


    state = fields.Selection(

        [
            ('draft', 'Brouillon'),
            ('quotation', 'Devis'),
            ('confirmed', 'Confirmé'),
            ('preparation', 'Préparation'),
            ('in_progress', 'En cours'),
            ('done', 'Terminé'),
            ('archived', 'Archivé')
        ],

        string='Etat',

        default='draft',

        tracking=True
    )


    notes = fields.Text(
        string='Notes'
    )


    # ==================================================
    # Budget
    # ==================================================

    budget_estimated = fields.Float(
        string='Budget estimé',
        help="Budget prévu avant l'événement"
    )


    budget_actual = fields.Float(
        string='Budget réel',
        compute='_compute_budget_actual',
        store=True
    )


    budget_difference = fields.Float(
        string='Écart budget',
        compute='_compute_budget_difference',
        store=True
    )


    company_id = fields.Many2one(
        'res.company',
        string='Société',
        default=lambda self: self.env.company
    )



    # ==================================================
    # Relations
    # ==================================================

    event_line_ids = fields.One2many(
        'event.catering.event.line',
        'event_id',
        string='Prestations'
    )


    staff_allocation_ids = fields.One2many(
        'event.catering.staff.allocation',
        'event_id',
        string='Personnel'
    )



    # ==================================================
    # Calculs
    # ==================================================

    total_cost = fields.Float(
        string='Coût prestations',
        compute='_compute_total_cost',
        store=True
    )


    recommended_staff = fields.Integer(
        string='Personnel recommandé',
        compute='_compute_recommended_staff',
        store=True
    )



    @api.depends('event_line_ids.total_price')
    def _compute_total_cost(self):

        for record in self:

            record.total_cost = sum(
                record.event_line_ids.mapped(
                    'total_price'
                )
            )



    @api.depends('total_cost')
    def _compute_budget_actual(self):

        for record in self:

            record.budget_actual = record.total_cost



    @api.depends(
        'budget_estimated',
        'budget_actual'
    )
    def _compute_budget_difference(self):

        for record in self:

            record.budget_difference = (
                record.budget_estimated
                -
                record.budget_actual
            )



    @api.depends(
        'guests_count',
        'event_type_id'
    )
    def _compute_recommended_staff(self):

        for record in self:

            if record.event_type_id and record.guests_count:

                ratio = (
                    record.event_type_id.staff_ratio
                    or 10
                )

                record.recommended_staff = max(
                    1,
                    int(
                        record.guests_count / ratio
                    )
                )

            else:

                record.recommended_staff = 0



    # ==================================================
    # Workflow
    # ==================================================

    def action_confirm(self):

        self.ensure_one()


        if self.date_end <= self.date_start:

            raise ValidationError(
                _("La date de fin doit être après la date de début.")
            )


        if not self.event_line_ids:

            raise UserError(
                _("Ajoutez au moins une prestation avant confirmation.")
            )


        self._check_conflicts()

        self._check_availability()


        self.state = 'confirmed'


        self._notify_responsible()


        return self._generate_quotation()



    def action_prepare(self):

        self.state = 'preparation'



    def action_start(self):

        self.state = 'in_progress'



    def action_done(self):

        self.state = 'done'



    def action_archive(self):

        self.state = 'archived'



    def action_reset_to_draft(self):

        self.state = 'draft'



    # ==================================================
    # Contrôle stock
    # ==================================================

    def _check_availability(self):

        for line in self.event_line_ids:

            product = line.product_id


            if (
                product.type == 'product'
                and product.qty_available < line.quantity
            ):

                raise ValidationError(

                    _(
                    "Stock insuffisant pour %s"
                    )
                    %
                    product.name

                )



    # ==================================================
    # Contrôle conflits réservation
    # ==================================================

    def _check_conflicts(self):


        conflicts = self.search(
            [

                ('id','!=',self.id),

                ('state','in',
                    [
                        'confirmed',
                        'preparation',
                        'in_progress'
                    ]
                ),

                ('date_start','<',self.date_end),

                ('date_end','>',self.date_start),

            ]
        )


        for event in conflicts:


            if self.room and event.room == self.room:

                raise ValidationError(

                    _(
                    "La salle %s est déjà réservée pour %s"
                    )
                    %
                    (
                        self.room,
                        event.name
                    )

                )



            if (
                self.responsible_id
                and
                event.responsible_id ==
                self.responsible_id
            ):

                raise ValidationError(

                    _(
                    "Le responsable %s est déjà affecté à %s"
                    )
                    %
                    (
                        self.responsible_id.name,
                        event.name
                    )

                )


            raise ValidationError(

                _(
                "Conflit horaire avec l'événement %s"
                )
                %
                event.name

            )



    # ==================================================
    # Notification
    # ==================================================

    def _notify_responsible(self):

        if self.responsible_id and self.responsible_id.user_id:

            self.message_post(

                body=_(
                "L'événement %s est confirmé."
                )
                %
                self.name,


                partner_ids=[
                    self.responsible_id.user_id.partner_id.id
                ]

            )



    # ==================================================
    # Création devis
    # ==================================================

    def _generate_quotation(self):


        sale_order = self.env['sale.order'].create(

            {

                'partner_id':
                    self.client_id.id,


                'user_id':
                    self.env.user.id,


                'date_order':
                    fields.Datetime.now(),


                'note':
                    f"Devis événement : {self.name}",


                'company_id':
                    self.company_id.id,

            }

        )


        for line in self.event_line_ids:


            self.env['sale.order.line'].create(

                {

                    'order_id':
                        sale_order.id,


                    'product_id':
                        line.product_id.id,


                    'product_uom_qty':
                        line.quantity,


                    'price_unit':
                        line.unit_price,


                    'name':
                        line.product_id.name,

                }

            )


        return sale_order
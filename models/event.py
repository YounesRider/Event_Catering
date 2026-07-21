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
    # Planification
    # ==================================================

    priority = fields.Selection(
    [
        ('1', 'Faible'),
        ('2', 'Normale'),
        ('3', 'Haute'),
        ('4', 'Urgente'),
        ('5', 'Critique'),
        ('6', 'Très critique'),
    ],
    string='Priorité',
    default='1',
    tracking=True
)

    color = fields.Integer(
        string="Couleur"
    )

    duration = fields.Float(
        string="Durée (heures)",
        compute="_compute_duration",
        store=True,
    )

    # ==================================================
    # Budget
    # ==================================================

    budget_estimated = fields.Float(
        string='Budget estimé',
        help="Budget prévu avant l'événement"
    )

    budget_actual = fields.Float(
        string='Budget actuel',
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
                record.event_line_ids.mapped('total_price')
            )

    @api.depends('total_cost')
    def _compute_budget_actual(self):
        for record in self:
            record.budget_actual = record.total_cost

    @api.depends('budget_estimated', 'budget_actual')
    def _compute_budget_difference(self):
        for record in self:
            record.budget_difference = (
                record.budget_estimated - record.budget_actual
            )

    @api.depends('guests_count', 'event_type_id')
    def _compute_recommended_staff(self):
        for record in self:
            if record.event_type_id and record.guests_count:
                ratio = record.event_type_id.staff_ratio or 10
                record.recommended_staff = max(
                    1,
                    int(record.guests_count / ratio)
                )
            else:
                record.recommended_staff = 0

    @api.depends('date_start', 'date_end')
    def _compute_duration(self):
        for record in self:
            if record.date_start and record.date_end:
                delta = record.date_end - record.date_start
                record.duration = delta.total_seconds() / 3600
            else:
                record.duration = 0

    # ==================================================
    # Workflow
    # ==================================================

    def action_confirm(self):
        self.ensure_one()

        # 1. Vérifier que date_end > date_start
        if self.date_end <= self.date_start:
            raise ValidationError(
                _("La date de fin doit être après la date de début.")
            )

        # 2. Vérifier qu'il existe au moins une prestation
        if not self.event_line_ids:
            raise UserError(
                _("Ajoutez au moins une prestation avant confirmation.")
            )

        # 3. Vérifier les conflits de réservation
        self._check_conflicts()

        # 4. Vérifier la disponibilité du stock
        self._check_availability()

        # 5. Passer l'état à confirmed
        self.state = 'confirmed'

        # 6. Envoyer la notification
        self._notify_responsible()

        # 7. Générer le devis
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
                    _("Stock insuffisant pour %s") % product.name
                )

    # ==================================================
    # Contrôle conflits réservation (bloquant)
    # ==================================================

    def _check_conflicts(self):
        """
        Contrôle bloquant des conflits de réservation.
        Levée d'une ValidationError si un conflit est détecté.
        """
        self.ensure_one()

        # Domaine commun : tous les événements sauf archivés
        domain = [
            ('id', '!=', self.id),
            ('date_start', '<', self.date_end),
            ('date_end', '>', self.date_start),
            ('state', '!=', 'archived'),
        ]

        # 1. Vérifier les conflits de responsable
        if self.responsible_id:
            employee_conflict = self.search(
                domain + [('responsible_id', '=', self.responsible_id.id)],
                limit=1
            )

            if employee_conflict:
                raise ValidationError(_(
                    "Le responsable '%s' est déjà affecté à l'événement '%s' "
                    "sur cette période.\n\n"
                    "Veuillez vérifier le calendrier."
                ) % (
                    self.responsible_id.name,
                    employee_conflict.name
                ))

        # 2. Vérifier les conflits de personnel affecté
        if self.staff_allocation_ids:
            for allocation in self.staff_allocation_ids:
                employee = allocation.employee_id
                if employee:
                    # Rechercher les événements où cet employé est affecté
                    employee_conflict = self.search(
                        domain + [
                            ('staff_allocation_ids.employee_id', '=', employee.id)
                        ],
                        limit=1
                    )

                    if employee_conflict:
                        raise ValidationError(_(
                            "L'employé '%s' est déjà affecté à l'événement '%s' "
                            "sur cette période.\n\n"
                            "Veuillez vérifier le calendrier."
                        ) % (
                            employee.name,
                            employee_conflict.name
                        ))

        # 3. Vérifier les conflits de salle (si une salle est renseignée)
        if self.room:
            room_conflict = self.search(
                domain + [('room', '=', self.room)],
                limit=1
            )

            if room_conflict:
                raise ValidationError(_(
                    "La salle '%s' est déjà réservée pour l'événement '%s' "
                    "sur cette période.\n\n"
                    "Veuillez vérifier le calendrier."
                ) % (
                    self.room,
                    room_conflict.name
                ))

    # ==================================================
    # Contrôle conflits réservation (non-bloquant)
    # ==================================================

    @api.onchange('date_start', 'date_end', 'room', 'responsible_id', 'staff_allocation_ids')
    def _onchange_check_conflicts(self):
        """
        Contrôle dynamique des conflits de réservation.
        Affiche un warning dans le formulaire sans bloquer l'enregistrement.
        """
        if not self.date_start or not self.date_end:
            return

        # Domaine commun : tous les événements sauf archivés
        domain = [
            ('id', '!=', self.id),
            ('date_start', '<', self.date_end),
            ('date_end', '>', self.date_start),
            ('state', '!=', 'archived'),
        ]

        # 1. Vérifier les conflits de responsable
        if self.responsible_id:
            employee_conflict = self.search(
                domain + [('responsible_id', '=', self.responsible_id.id)],
                limit=1
            )

            if employee_conflict:
                return {
                    'warning': {
                        'title': _("Conflit de planning"),
                        'message': _(
                            "Un conflit existe avec l'événement '%s'.\n\n"
                            "Veuillez vérifier le calendrier avant confirmation."
                        ) % employee_conflict.name
                    }
                }

        # 2. Vérifier les conflits de personnel affecté
        if self.staff_allocation_ids:
            for allocation in self.staff_allocation_ids:
                employee = allocation.employee_id
                if employee:
                    employee_conflict = self.search(
                        domain + [
                            ('staff_allocation_ids.employee_id', '=', employee.id)
                        ],
                        limit=1
                    )

                    if employee_conflict:
                        return {
                            'warning': {
                                'title': _("Conflit de planning"),
                                'message': _(
                                    "Un conflit existe avec l'événement '%s'.\n\n"
                                    "Veuillez vérifier le calendrier avant confirmation."
                                ) % employee_conflict.name
                            }
                        }

        # 3. Vérifier les conflits de salle (si une salle est renseignée)
        if self.room:
            room_conflict = self.search(
                domain + [('room', '=', self.room)],
                limit=1
            )

            if room_conflict:
                return {
                    'warning': {
                        'title': _("Conflit de planning"),
                        'message': _(
                            "Un conflit existe avec l'événement '%s'.\n\n"
                            "Veuillez vérifier le calendrier avant confirmation."
                        ) % room_conflict.name
                    }
                }

    # ==================================================
    # Notification
    # ==================================================

    def _notify_responsible(self):
        if self.responsible_id and self.responsible_id.user_id:
            self.message_post(
                body=_("L'événement %s est confirmé.") % self.name,
                partner_ids=[self.responsible_id.user_id.partner_id.id]
            )

    # ==================================================
    # Création devis
    # ==================================================

    def _generate_quotation(self):
        sale_order = self.env['sale.order'].create({
            'partner_id': self.client_id.id,
            'user_id': self.env.user.id,
            'date_order': fields.Datetime.now(),
            'note': f"Devis événement : {self.name}",
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
from odoo.tests import TransactionCase
from odoo.exceptions import ValidationError

class TestEventCatering(TransactionCase):
    
    def setUp(self):
        super(TestEventCatering, self).setUp()
        self.Event = self.env['event.catering.event']
        self.EventType = self.env['event.catering.type']
        self.Product = self.env['product.product']
        self.Partner = self.env['res.partner']
        
        # Création d'un type d'événement
        self.type = self.EventType.create({
            'name': 'Test Type',
            'staff_ratio': 10.0,
            'preparation_time': 2.0
        })
        
        # Création d'un client
        self.client = self.Partner.create({
            'name': 'Test Client',
            'is_company': True
        })
        
        # Création d'un produit
        self.product = self.Product.create({
            'name': 'Test Product',
            'list_price': 100.0,
            'type': 'product'
        })
    
    def test_create_event(self):
        event = self.Event.create({
            'name': 'Test Event',
            'client_id': self.client.id,
            'event_type_id': self.type.id,
            'date_start': '2025-06-15 18:00:00',
            'date_end': '2025-06-15 23:00:00',
            'guests_count': 100,
        })
        self.assertEqual(event.state, 'draft')
        self.assertTrue(event.reference)
    
    def test_recommended_staff(self):
        event = self.Event.create({
            'name': 'Test Event Staff',
            'client_id': self.client.id,
            'event_type_id': self.type.id,
            'date_start': '2025-06-15 18:00:00',
            'date_end': '2025-06-15 23:00:00',
            'guests_count': 100,
        })
        self.assertEqual(event.recommended_staff, 10)
        
        event.guests_count = 150
        self.assertEqual(event.recommended_staff, 15)
    
    def test_event_confirmation(self):
        event = self.Event.create({
            'name': 'Test Event Confirm',
            'client_id': self.client.id,
            'event_type_id': self.type.id,
            'date_start': '2025-06-15 18:00:00',
            'date_end': '2025-06-15 23:00:00',
            'guests_count': 50,
        })
        
        # Ajouter une ligne de prestation
        self.env['event.catering.event.line'].create({
            'event_id': event.id,
            'product_id': self.product.id,
            'quantity': 10,
        })
        
        event.action_confirm()
        self.assertEqual(event.state, 'confirmed')
    
    def test_conflict_detection(self):
        # Créer le premier événement
        event1 = self.Event.create({
            'name': 'Event 1',
            'client_id': self.client.id,
            'event_type_id': self.type.id,
            'date_start': '2025-06-15 18:00:00',
            'date_end': '2025-06-15 23:00:00',
            'guests_count': 50,
        })
        event1.action_confirm()
        
        # Créer le deuxième événement en conflit
        event2 = self.Event.create({
            'name': 'Event 2',
            'client_id': self.client.id,
            'event_type_id': self.type.id,
            'date_start': '2025-06-15 19:00:00',
            'date_end': '2025-06-15 22:00:00',
            'guests_count': 30,
        })
        
        # Vérifier que la confirmation lève une erreur
        with self.assertRaises(ValidationError):
            event2.action_confirm()
{
    'name': 'Event Catering',
    'version': '18.0.1.0.0',
    'category': 'Operations',
    'sequence': 1,
    'summary': 'Event Management for Catering Companies',
    'description': """
        Module for comprehensive event management:
        - Event creation and tracking
        - Service and staff management
        - Intelligent resource allocation
        - Dashboard and KPI
        - Calendar and Kanban views
    """,
    'author': 'younes',
    'website': 'https://www.votreentreprise.com',
    'depends': [
        'base',
        'contacts',
        'sale',
        'stock',
        'purchase',
        'calendar',
        'hr',
        'mail',
        'web',
    ],

    'data': [
        'security/event_security.xml',
        'security/ir.model.access.xml',

        'data/event_sequence.xml',
        'data/event_type_data.xml',

        'views/action.xml',
        'views/event_type_views.xml',
        'views/event_views.xml',
        'views/menu_views.xml',

        'reports/event_report.xml',
    ],

    'assets': {

        'web.assets_backend': [

            'event_catering/static/src/css/dashboard.css',
            'event_catering/static/src/js/dashboard.js',
            'event_catering/static/src/xml/dashboard.xml',

        ],

    },
    'demo': [],
    'installable': True,
    'application': True,
    'auto_install': False,
    'license': 'LGPL-3'
}
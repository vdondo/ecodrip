# -*- coding: utf-8 -*-

{
    'name': 'Eco-Drip: Customization of checks layout',
    'summary': 'Eco-Drip: Customization of checks layout',
    'sequence': 100,
    'license': 'OEEL-1',
    'website': 'https://www.odoo.com',
    'version': '1.1',
    'author': 'Odoo Inc',
    'description': """
        Task ID: 2438708
        - Changes
    """,
    'category': 'Custom Development',

    # any module necessary for this one to work correctly
    'depends': ['account', 'l10n_us_check_printing'],
    'data': [
        'views/account_invoice_views.xml',
        'views/print_check.xml',
        'views/res_config_settings_views.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
}

# -*- coding: utf-8 -*-
{
    'name': "ym_kasbon",

    'summary': """
        Short (1 phrase/line) summary of the module's purpose, used as
        subtitle on modules listing or apps.openerp.com""",

    'description': """
        Long description of module's purpose
    """,

    'author': "Yastaqiim Muqorrobin - 085156973123",
    'website': "Freelance  - 085156973123",

    # Categories can be used to filter modules in modules listing
    # Check https://github.com/odoo/odoo/blob/16.0/odoo/addons/base/data/ir_module_category_data.xml
    # for the full list
    'category': 'Uncategorized',
    'version': '0.1',

    # any module necessary for this one to work correctly
    'depends': ['base', 'base_setup', 'account', 'hr', 'analytic', 'account_accountant', 'digest'],

    # always loaded
    'data': [
        'security/ir.model.access.csv',
        'security/security.xml',
        'views/report_bukti_bank_keluar.xml',
        'views/report_bukti_bank_masuk.xml',
        'views/report_bukti_kas_keluar.xml',
        'views/report_bukti_kas_masuk.xml',
        'views/report_kasbon.xml',
        'views/report_lpj_kasbon.xml',
        'views/views.xml',
        'views/templates.xml',
    ],
    # only loaded in demonstration mode
    'demo': [
        'demo/demo.xml',
    ],
}

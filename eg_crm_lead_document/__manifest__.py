{
    'name': 'CRM Lead Document',
    'version': '16.0',
    'category': 'CRM',
    "summary": "CRM Lead Document",
    'depends': ['crm'],
    "author": 'INKERP',
    "website": 'https://www.inkerp.com/',
    
    'data': [
        'security/ir.model.access.csv',
        'wizard/crm_document_view.xml',
        'views/crm_lead_view.xml',
    ],
    
    'images': ['static/description/banner.png'],
    'license': "OPL-1",
    'installable': True,
    'application': True,
    'auto_install': False,
}

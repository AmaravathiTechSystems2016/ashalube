{
    'name': 'CRM Dashboard',
    'version': '19.0.1.0.0',
    'category': 'Sales/CRM',
    'summary': 'CRM pipeline dashboard on the Sales spreadsheet dashboard',
    'depends': [
        'spreadsheet_dashboard_sale',
        'crm',
        'sale_crm',
    ],
    'data': [
        'data/crm_tag_data.xml',
        'views/crm_lead_views.xml',
        'views/sale_order_views.xml',
        'data/dashboards.xml',
    ],
    'installable': True,
    'application': False,
    'license': 'LGPL-3',
    'assets': {
        'spreadsheet.o_spreadsheet': [
            'al_crm_dashboard/static/src/dashboard_sheet_tabs.js',
            'al_crm_dashboard/static/src/dashboard_sheet_tabs.xml',
        ],
        'web.assets_backend': [
            'al_crm_dashboard/static/src/dashboard_sheet_tabs.scss',
        ],
    },
}

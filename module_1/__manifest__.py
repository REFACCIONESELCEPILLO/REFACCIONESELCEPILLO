# -*- coding: utf-8 -*-
{
    'name': 'design_ticket_sale',
    'version': '18.0.4.0.0',
    'summary': 'Diseño térmico para órdenes de venta',
    'description': 'Personaliza exclusivamente el ticket de orden de venta de El Cepillo.',
    'author': 'IcTechnologyMx',
    'license': 'LGPL-3',
    'category': 'Sales/Sales',
    'depends': [
        'sale',
        'sale_stock',
    ],
    'data': [
        'report/sale_ticket_report.xml',
    ],
    'assets': {
        'web.report_assets_common': [
            'module_1/static/src/scss/sale_ticket_report.scss',
        ],
    },
    'auto_install': False,
    'application': False,
    'installable': True,
}

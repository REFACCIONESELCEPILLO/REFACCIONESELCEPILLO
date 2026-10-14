# -*- coding: utf-8 -*-
{
    'name': 'design_ticket_sale',
    'version': '18.0.4.4.0',
    'summary': 'Ticket de venta y marca en reportes de venta y factura',
    'description': 'Personaliza el ticket de El Cepillo y muestra la marca de autoparte en tickets, órdenes de venta y facturas.',
    'author': 'IcTechnologyMx',
    'license': 'LGPL-3',
    'category': 'Sales/Sales',
    'depends': [
        'sale',
        'sale_stock',
        'account',
        'sh_product_brand_sale',
    ],
    'data': [
        'report/sale_ticket_report.xml',
        'report/product_brand_reports.xml',
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

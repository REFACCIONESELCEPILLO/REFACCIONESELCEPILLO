# -*- coding: utf-8 -*-
{
    'name': 'Diseño de Ticket El Cepillo',
    'version': '18.0.2.1.0',
    'summary': 'Diseño térmico para órdenes de venta',
    'description': 'Personaliza exclusivamente el ticket de orden de venta de El Cepillo.',
    'author': 'IcTechnologyMx',
    'license': 'LGPL-3',
    'category': 'Sales/Sales',
    'depends': [
        # Garantiza que el reemplazo de inventario se instale antes de
        # retirar las vistas legadas durante la migración de module_1.
        'product_qty_warehouse',
        'sale',
    ],
    'data': [
        'report/sale_ticket_report.xml',
    ],
    'assets': {
        'web.report_assets_common': [
            'module_1/static/src/scss/sale_ticket_report.scss',
        ],
    },
    'application': False,
    'installable': True,
}

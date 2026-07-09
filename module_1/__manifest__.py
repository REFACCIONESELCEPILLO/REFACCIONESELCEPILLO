# -*- coding: utf-8 -*-
{
    'name': 'Product Qty Warehouse',
    'version': '18.0.1.0.2',
    'summary': 'Muestra disponibilidad libre de productos por almacen',
    'description': 'Disponibilidad de producto por almacen para Odoo 18.',
    'author': 'IcTechnologyMx',
    'license': 'LGPL-3',
    'category': 'Inventory/Inventory',
    'depends': [
        'product',
        'sales_team',
        'stock',
    ],
    'data': [
        'security/ir.model.access.csv',
        'views/legacy_cleanup.xml',
        'views/product_warehouse_availability_views.xml',
        'views/product_template_view.xml',
    ],
    'application': False,
    'installable': True,
} 

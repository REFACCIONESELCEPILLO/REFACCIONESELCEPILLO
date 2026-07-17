# -*- coding: utf-8 -*-
{
    'name': 'Product Qty Warehouse',
    'version': '18.0.1.0.8',
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
        'views/product_warehouse_availability_views.xml',
        'views/product_template_view.xml',
    ],
    'pre_init_hook': 'pre_init_hook',
    'application': False,
    'installable': True,
} 

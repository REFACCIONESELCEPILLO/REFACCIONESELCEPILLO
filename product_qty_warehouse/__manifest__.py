# -*- coding: utf-8 -*-
{
    'name': 'Product Qty Warehouse Compatibility',
    'version': '18.0.1.0.0',
    'summary': 'Alias tecnico para el modulo de existencias por almacen',
    'description': """
Modulo puente para conservar el nombre tecnico product_qty_warehouse.
La funcionalidad real se mantiene en module_1 para no romper bases donde ya
esta instalado.
    """,
    'author': 'IcTechnologyMx',
    'license': 'LGPL-3',
    'category': 'Inventory/Inventory',
    'depends': [
        'module_1',
    ],
    'data': [],
    'application': False,
    'installable': True,
}


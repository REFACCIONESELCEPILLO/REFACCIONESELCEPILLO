# -*- coding: utf-8 -*-
{
    "name": "ICK Auto Part Vehicle Product Kanban",
    "version": "18.0.1.3.1",
    "summary": "Acceso kanban a productos sugeridos, accesorios y opcionales",
    "author": "ICKAB",
    "website": "https://ickab.mx",
    "category": "Inventory/Products",
    "license": "LGPL-3",
    "depends": [
        "sh_auto_part_vehicle_extends",
        "sh_product_brand_sale",
        "product_qty_warehouse",
        "website_sale",
    ],
    "data": [
        "views/product_template_views.xml",
    ],
    "assets": {
        "web.assets_backend": [
            "ick_auto_part_vehicle_product_kanban/static/src/js/product_kanban_tools.js",
            "ick_auto_part_vehicle_product_kanban/static/src/xml/product_kanban_tools.xml",
            "ick_auto_part_vehicle_product_kanban/static/src/scss/product_kanban.scss",
        ],
    },
    "installable": True,
    "application": False,
}

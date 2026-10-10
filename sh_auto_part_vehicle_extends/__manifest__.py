# -*- coding: utf-8 -*-
{
    "name": "Auto Part Vehicle Extensions",
    "summary": "Extensiones Ickab para autopartes, tienda y busqueda OEM",
    "description": """
Extiende All In One Auto Parts Management con reglas propias de Ickab:
SKU en tienda, busqueda por OEM y cintillos de disponibilidad por almacen.
    """,
    "version": "18.0.1.3.0",
    "author": "Ickab",
    "category": "Website/eCommerce",
    "license": "LGPL-3",
    "depends": [
        "sh_auto_part_vehicle",
        "product_qty_warehouse",
        "sale_management",
        "website_sale",
        "stock",
    ],
    "data": [
        "data/backend_assets.xml",
        "views/product_template_views.xml",
        "views/website_sale_templates.xml",
    ],
    "assets": {
        "web.assets_backend": [
            "sh_auto_part_vehicle_extends/static/src/js/kanban_compatibility.js",
            "sh_auto_part_vehicle_extends/static/src/xml/kanban_compatibility.xml",
            "sh_auto_part_vehicle_extends/static/src/scss/kanban_compatibility.scss",
        ],
        "web.assets_frontend": [
            "sh_auto_part_vehicle_extends/static/src/scss/website_sale.scss",
        ],
    },
    "application": False,
    "installable": True,
}

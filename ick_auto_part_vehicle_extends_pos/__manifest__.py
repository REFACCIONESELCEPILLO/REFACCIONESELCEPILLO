# -*- coding: utf-8 -*-
{
    "name": "ICK Auto Part Vehicle Extends POS",
    "version": "18.0.2.0.1",
    "summary": "Asistente contextual de autopartes para el punto de venta",
    "category": "Point of Sale",
    "author": "ICKAB",
    "website": "https://ickab.mx",
    "license": "LGPL-3",
    "depends": [
        "point_of_sale",
        "sh_auto_part_vehicle",
        "sh_auto_part_vehicle_extends",
        "sh_product_brand_sale",
        "product_qty_warehouse",
    ],
    "data": [
        "data/pos_assets.xml",
        "views/res_config_settings_views.xml",
    ],
    "assets": {
        "point_of_sale._assets_pos": [
            "ick_auto_part_vehicle_extends_pos/static/src/app/product_preview.js",
            "ick_auto_part_vehicle_extends_pos/static/src/app/product_preview.xml",
            "ick_auto_part_vehicle_extends_pos/static/src/app/auto_parts_panel.js",
            "ick_auto_part_vehicle_extends_pos/static/src/app/auto_parts_panel.xml",
            "ick_auto_part_vehicle_extends_pos/static/src/app/product_info.xml",
            "ick_auto_part_vehicle_extends_pos/static/src/app/auto_parts_panel.scss",
        ],
    },
    "installable": True,
    "application": False,
}

{
    "name": "POS Internal References",
    "version": "18.0.2.0.0",
    "author": "AskByte Technolab; adapted by ICKAB",
    "summary": "Configurable product identification in Point of Sale",
    "category": "Point of Sale",
    "depends": ["point_of_sale", "sh_auto_part_vehicle"],
    "data": [
        "views/res_config_settings_views.xml",
    ],
    "assets": {
        "point_of_sale._assets_pos": [
            "abt_pos_internal_reference/static/src/app/screens/product_screen/product_screen.js",
            "abt_pos_internal_reference/static/src/app/models/pos_order_line.js",
        ],
    },
    "images": ["static/description/thumbnail.png"],
    "license": "LGPL-3",
    "application": True,
    "installable": True,
    "auto_install": False,
}

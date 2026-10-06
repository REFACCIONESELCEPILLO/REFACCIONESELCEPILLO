{
    "name": "ICKAB POS Product Catalog",
    "version": "18.0.1.0.4",
    "summary": "Responsive product cards and receipt formatting for Point of Sale",
    "category": "Point of Sale",
    "author": "ICKAB",
    "license": "LGPL-3",
    "depends": ["point_of_sale"],
    "data": ["views/res_config_settings_views.xml"],
    "assets": {
        "point_of_sale._assets_pos": [
            "ickab_pos_product_catalog/static/src/app/product_catalog.js",
            "ickab_pos_product_catalog/static/src/app/product_catalog.xml",
            "ickab_pos_product_catalog/static/src/app/product_catalog.scss",
            "ickab_pos_product_catalog/static/src/app/receipt_format.js",
            "ickab_pos_product_catalog/static/src/app/receipt_format.xml",
        ],
    },
    "installable": True,
    "application": False,
}

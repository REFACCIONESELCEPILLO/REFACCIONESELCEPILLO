{
    "name": "Mocalli | Configurador dimensional, MRP y compras",
    "version": "18.0.2.1.0",
    "summary": "Configura productos por dimensiones y genera componentes exactos para fabricación",
    "category": "Manufacturing/Manufacturing",
    "license": "OPL-1",
    "depends": [
        "account",
        "mrp",
        "product",
        "purchase_stock",
        "sale_management",
        "sale_stock",
        "stock",
    ],
    "data": [
        "views/dps_sale_order_line.xml",
        "views/product_dimension_views.xml",
        "views/mrp_production_views.xml",
        "reports/dps_sale_order_report.xml",
    ],
    "assets": {
        "web.assets_backend": [
            "product_dimension/static/src/js/sale_product_field.js",
            "product_dimension/static/src/js/product_template_attribute_line.js",
            "product_dimension/static/src/xml/product_template_attribute_line.xml",
            "product_dimension/static/src/scss/product_configurator.scss",
        ],
    },
    "images": ["static/description/icon.png"],
    "installable": True,
    "auto_install": False,
    "application": False,
}

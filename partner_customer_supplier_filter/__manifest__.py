{
    "name": "Clasificacion de clientes y proveedores",
    "version": "18.0.1.0.0",
    "summary": "Clasifica y filtra automaticamente clientes y proveedores",
    "category": "Sales/Contacts",
    "author": "Refacciones El Cepillo",
    "license": "LGPL-3",
    "depends": [
        "account",
        "contacts",
        "sale_management",
        "purchase",
        "product",
    ],
    "data": [
        "views/res_partner_views.xml",
        "views/sale_order_views.xml",
        "views/purchase_order_views.xml",
        "views/product_supplierinfo_views.xml",
    ],
    "post_init_hook": "post_init_hook",
    "installable": True,
    "application": False,
}

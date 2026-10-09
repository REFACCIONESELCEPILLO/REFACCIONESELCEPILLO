# -*- coding: utf-8 -*-
{
    'name': 'ICK Auto Part Vehicle Extends Sale',
    'version': '18.0.3.4.1',
    'summary': 'Panel lateral de refacciones y accesorios para cotizaciones '
               'de autopartes',
    'description': """
ICK Auto Part Vehicle Extends Sale
==================================

Extiende el formulario de cotizaciones de venta (``sale.order``) para el giro
de refacciones automotrices.

Características
---------------
- Producto activo contextual sincronizado con las líneas de la cotización.
- Panel lateral con sugerencias de:
  * Piezas compatibles con el vehículo seleccionado.
  * Equivalencias por código OEM.
  * Opcionales, accesorios y alternativas definidas en el catálogo.
- Precio de la pricelist de la cotización, disponibilidad por almacén y
  marca de autoparte en cada tarjeta.
- Botón "Agregar" que añade el producto a las líneas de la cotización.
- Botón de compatibilidad que abre las reglas (vehículos) de un producto.
- Marca tomada de ``sh_product_brand_sale`` en líneas y recomendaciones.
- Disponibilidad vendible en las líneas, con desglose por almacén.
- Alta directa de piezas con variante única; sus opcionales se administran
  desde el asistente sin abrir el configurador estándar.

Reutiliza sin modificar los módulos existentes ``sh_auto_part_vehicle``,
``sh_auto_part_vehicle_extends``, ``sh_product_brand_sale`` y
``product_qty_warehouse``.
""",
    'author': 'ICKAB',
    'website': 'https://ickab.mx',
    'maintainer': 'ICKAB',
    'category': 'Sales/Sales',
    'license': 'LGPL-3',
    'depends': [
        'sale_management',
        'sale_stock',
        'sh_auto_part_vehicle',
        'sh_auto_part_vehicle_extends',
        'sh_product_brand_sale',
        'product_qty_warehouse',
    ],
    'data': [
        'views/sale_order_views.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'ick_auto_part_vehicle_extends_sale/static/src/scss/auto_sale.scss',
            'ick_auto_part_vehicle_extends_sale/static/src/js/auto_parts_panel.js',
            'ick_auto_part_vehicle_extends_sale/static/src/js/compatibility_dialog.js',
            'ick_auto_part_vehicle_extends_sale/static/src/js/stock_dialog.js',
            'ick_auto_part_vehicle_extends_sale/static/src/xml/auto_parts_panel.xml',
            'ick_auto_part_vehicle_extends_sale/static/src/xml/compatibility_dialog.xml',
            'ick_auto_part_vehicle_extends_sale/static/src/xml/stock_dialog.xml',
            'ick_auto_part_vehicle_extends_sale/static/src/js/form_compiler.js',
        ],
    },
    'installable': True,
    'application': False,
    'auto_install': False,
}

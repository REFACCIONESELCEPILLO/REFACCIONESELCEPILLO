# -*- coding: utf-8 -*-
{
    "name": "Auto Part Vehicle Labels",
    "summary": "Motor unificado de etiquetas de autopartes con render ZPL/TSPL",
    "description": """
Auto Part Vehicle Labels
========================

Complemento para ``sh_auto_part_vehicle`` orientado a la impresión de etiquetas
para refaccionarias.

Características principales:
- Etiquetas de 50 x 30 mm y 70 x 50 mm con render nativo ZPL o TSPL según impresora.
- Resoluciones 203 dpi y 300 dpi.
- Vista previa proporcional antes de imprimir.
- SKU / referencia interna del producto.
- Nombre del producto.
- El formato 50 x 30 mm prioriza SKU, nombre y OEM y no imprime código de barras.
- El formato 70 x 50 mm conserva Code 128 para quienes lo requieran.
- Referencias OEM y marca/proveedor desde ``vehicle_oem_lines``.
- TSPL usa TEXT/BARCODE nativos.
- Impresión directa multi-impresora mediante ICKAB Direct Print.

El módulo no modifica el código de Softhealer; consume los campos publicados por
``sh_auto_part_vehicle``.
    """,
    "version": "18.0.1.0.0",
    "category": "Inventory/Inventory",
    "author": "ICKAB",
    "license": "LGPL-3",
    "depends": [
        "product",
        "stock",
        "sh_auto_part_vehicle",
        "ickab_direct_print",
    ],
    "data": [
        "report/label_report_templates.xml",
        "report/label_report_actions.xml",
        "views/product_label_layout_views.xml",
    ],
    "installable": True,
    "application": False,
    "auto_install": False,
}

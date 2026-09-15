# -*- coding: utf-8 -*-
{
    'name': 'Product Barcode Generator-Rootlevel',
    'version': '18.0.19.0.2',
    'sequence': 10,
    'summary': 'Product Barcode Generator with structured unique generation and bulk completion',
    'description': """
    Product Barcode Generator - Rootlevel / ICKAB customization
    ------------------------------------------------------------
    - Generate product barcode with various formats available.
    - Single/bulk barcode generation from form/list view.
    - Configurable company prefix and up to three category levels.
    - 00 reserved for missing category levels.
    - Global sequence + permanent history to avoid reusing generated codes.
    - Bulk generation only fills products without barcode.
    - Quick Generate button beside product barcode field.
    - Barcode preview and built-in Spanish configuration manual.
    - Original addon developed by RootLevel Innovations Private Limited.
    """,
    'author': 'Rootlevel Innovations Private Limited; customized for ICKAB',
    'website': 'https://rootlevel.in',
    'category': 'Inventory/Inventory',
    'depends': ['stock'],
    'external_dependencies': {
        'python': ['barcode', 'PIL'],
    },
    'data': [
        'security/product_barcode_rl_security.xml',
        'security/ir.model.access.csv',
        'data/barcode_sequence.xml',
        'data/barcode_generation_cron.xml',
        'data/product_barcodes_report_rl.xml',
        'wizard/product_barcode_generator_rl.xml',
        'wizard/barcode_missing_image_generator_rl.xml',
        'wizard/barcode_bulk_generator_rl.xml',
        'views/product_category_views.xml',
        'views/product_template_views_extend.xml',
        'views/barcode_config_views.xml',
        'views/barcode_history_views.xml',
    ],
    'images': ['static/description/barcode_generator_cover_image.png'],
    'assets': {
        'web.assets_backend': [
            'barcode_generator_rl/static/fonts/DejaVuSans.ttf',
            'barcode_generator_rl/static/src/js/barcode_background_progress.js',
        ],
    },
    'installable': True,
    'application': True,
    'license': 'OPL-1',
}

{
    "name": "ICKAB Label Studio",
    "version": "18.0.5.3.1",
    "category": "Tools",
    "summary": "Diseñador WYSIWYG profesional de etiquetas para Odoo",
    "description": """
ICKAB Label Studio
==================
Diseñador profesional de etiquetas propiedad de ICKAB para Odoo 18.
El diseño maestro se almacena en medidas físicas y permanece independiente del
motor de impresión. Studio diseña, previsualiza, importa/exporta ZPL y expone un
contrato neutral para renderers y comunicación opcional con ICKAB Direct Print.
    """,
    "author": "ICKAB",
    "maintainer": "ICKAB",
    "website": "https://ickab.mx",
    "depends": ["base", "web", "product"],
    "external_dependencies": {"python": ["Pillow"]},
    "data": [
        "security/label_studio_security.xml",
        "security/ir.model.access.csv",
        "data/label_media_data.xml",
        "views/report_templates.xml",
        "views/zpl_import_views.xml",
        "views/label_template_views.xml",
        "views/product_label_layout_views.xml",
    ],
    "assets": {
        "web.assets_backend": [
            "ickab_label_studio/static/src/js/label_designer_field.js",
            "ickab_label_studio/static/src/xml/label_designer_field.xml",
            "ickab_label_studio/static/src/css/label_designer.css",
        ],
    },
    "license": "Other proprietary",
    "installable": True,
    "application": True,
    "auto_install": False,
}

from odoo import SUPERUSER_ID, api


MODULE_METADATA = {
    "shortdesc": "Mocalli | Configurador dimensional, MRP y compras",
    "summary": (
        "Configura productos por dimensiones y genera componentes exactos "
        "para fabricación"
    ),
}


def migrate(cr, version):
    """Replace stale translated metadata kept by older installations."""
    env = api.Environment(cr, SUPERUSER_ID, {})
    module = env["ir.module.module"].search([
        ("name", "=", "product_dimension"),
    ], limit=1)
    if not module:
        return

    module.with_context(lang=None).write({
        **MODULE_METADATA,
        "author": "Ickab",
        "maintainer": "Ickab",
    })
    for lang_code, _lang_name in env["res.lang"].get_installed():
        module.with_context(lang=lang_code).write(MODULE_METADATA)

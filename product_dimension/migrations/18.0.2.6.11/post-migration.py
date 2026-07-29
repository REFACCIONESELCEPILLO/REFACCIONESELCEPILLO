from odoo import SUPERUSER_ID, api


MODULE_METADATA = {
    "shortdesc": "Configurador dimensional",
}


def migrate(cr, version):
    env = api.Environment(cr, SUPERUSER_ID, {})
    module = env["ir.module.module"].search(
        [("name", "=", "product_dimension")], limit=1
    )
    if not module:
        return

    module.with_context(lang=None).write(MODULE_METADATA)
    for lang_code, _lang_name in env["res.lang"].get_installed():
        module.with_context(lang=lang_code).write(MODULE_METADATA)

from odoo import SUPERUSER_ID, api


def migrate(cr, version):
    """Unlock existing dimensional quotations blocked by sale_restring."""
    env = api.Environment(cr, SUPERUSER_ID, {})
    orders = env["sale.order"]
    if "blocked_order" not in orders._fields:
        return

    dimension_quotations = orders.search([
        ("blocked_order", "=", True),
        ("state", "in", ["draft", "sent"]),
        ("order_line.product_id.product_tmpl_id.dimension_enabled", "=", True),
    ])
    dimension_quotations._ensure_dimension_quotations_are_editable()

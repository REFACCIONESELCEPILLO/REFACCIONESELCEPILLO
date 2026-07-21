from odoo import SUPERUSER_ID, api


def migrate(cr, version):
    """Initialize editable metadata from components already assigned."""
    env = api.Environment(cr, SUPERUSER_ID, {})
    values = env["product.attribute.value"].with_context(active_test=False).search([
        ("component_product_id", "!=", False),
    ])
    for value in values:
        updates = {}
        if not value.component_internal_reference:
            updates["component_internal_reference"] = value.component_product_id.default_code
        if not value.component_cost:
            updates["component_cost"] = value.component_product_id.standard_price
        if updates:
            value.write(updates)

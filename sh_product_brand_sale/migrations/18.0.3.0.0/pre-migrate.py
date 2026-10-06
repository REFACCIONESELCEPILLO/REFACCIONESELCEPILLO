from odoo import SUPERUSER_ID, api


def migrate(cr, version):
    """Preserve assignments made with the retired duplicate brand catalog."""
    env = api.Environment(cr, SUPERUSER_ID, {})
    if not env.registry.get("product.brand"):
        return

    old_brands = env["product.brand"].search([])
    vehicle_brand = env["motorcycle.brand"]
    for old_brand in old_brands:
        target = vehicle_brand.search(
            [("name", "=ilike", old_brand.name)], limit=1
        ) or vehicle_brand.create({"name": old_brand.name})
        templates = env["product.template"].search(
            [("brand_id", "=", old_brand.id)]
        )
        templates.mapped("product_variant_ids").filtered(
            lambda product: not product.brand
        ).write({"brand": target.id})

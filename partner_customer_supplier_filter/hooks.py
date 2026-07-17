from odoo import Command


def post_init_hook(env):
    """Normalize existing partners without removing prior classifications."""
    Partner = env["res.partner"].with_context(active_test=False)
    categories = Partner._classification_categories()
    partners = Partner.search([])

    customer_partners = partners.filtered(
        lambda partner: partner.is_customer
        or partner.customer_rank > 0
        or categories["customer"] in partner.category_id
        or (
            "x_studio_es_cliente" in partner._fields
            and partner.x_studio_es_cliente
        )
    )
    supplier_partners = partners.filtered(
        lambda partner: partner.is_supplier
        or partner.supplier_rank > 0
        or categories["supplier"] in partner.category_id
        or (
            "x_studio_es_proveedor" in partner._fields
            and partner.x_studio_es_proveedor
        )
    )

    skip_context = {"skip_partner_classification_sync": True}
    if customer_partners:
        customer_values = {
            "is_customer": True,
            "category_id": [Command.link(categories["customer"].id)],
        }
        if "x_studio_es_cliente" in Partner._fields:
            customer_values["x_studio_es_cliente"] = True
        customer_partners.with_context(**skip_context).write(customer_values)
        customer_partners.filtered(
            lambda partner: partner.customer_rank < 1
        ).with_context(**skip_context).write({"customer_rank": 1})

    if supplier_partners:
        supplier_values = {
            "is_supplier": True,
            "category_id": [Command.link(categories["supplier"].id)],
        }
        if "x_studio_es_proveedor" in Partner._fields:
            supplier_values["x_studio_es_proveedor"] = True
        supplier_partners.with_context(**skip_context).write(supplier_values)
        supplier_partners.filtered(
            lambda partner: partner.supplier_rank < 1
        ).with_context(**skip_context).write({"supplier_rank": 1})

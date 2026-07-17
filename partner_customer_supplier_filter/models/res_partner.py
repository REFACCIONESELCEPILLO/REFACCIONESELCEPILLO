from odoo import Command, api, fields, models


class ResPartner(models.Model):
    _inherit = "res.partner"

    is_customer = fields.Boolean(
        string="Es cliente",
        index=True,
        help="Permite seleccionar este contacto como cliente en ventas.",
    )
    is_supplier = fields.Boolean(
        string="Es proveedor",
        index=True,
        help="Permite seleccionar este contacto como proveedor en compras.",
    )

    @api.model
    def _classification_categories(self):
        """Return the business categories, creating them when necessary."""
        Category = self.env["res.partner.category"].sudo()
        categories = {}
        for key, name in (("customer", "Cliente"), ("supplier", "Proveedor")):
            category = Category.search([("name", "=", name)], limit=1)
            if not category:
                category = Category.create({"name": name})
            categories[key] = category
        return categories

    def _sync_classification(self):
        """Keep module fields, Studio fields, tags and ranks consistent."""
        categories = self._classification_categories()
        has_studio_customer = "x_studio_es_cliente" in self._fields
        has_studio_supplier = "x_studio_es_proveedor" in self._fields

        for partner in self:
            values = {}
            category_commands = []

            if has_studio_customer:
                values["x_studio_es_cliente"] = partner.is_customer
            if has_studio_supplier:
                values["x_studio_es_proveedor"] = partner.is_supplier

            customer_category = categories["customer"]
            supplier_category = categories["supplier"]
            if partner.is_customer:
                if customer_category not in partner.category_id:
                    category_commands.append(Command.link(customer_category.id))
                if partner.customer_rank < 1:
                    values["customer_rank"] = 1
            elif customer_category in partner.category_id:
                category_commands.append(Command.unlink(customer_category.id))

            if partner.is_supplier:
                if supplier_category not in partner.category_id:
                    category_commands.append(Command.link(supplier_category.id))
                if partner.supplier_rank < 1:
                    values["supplier_rank"] = 1
            elif supplier_category in partner.category_id:
                category_commands.append(Command.unlink(supplier_category.id))

            if category_commands:
                values["category_id"] = category_commands
            if values:
                partner.with_context(skip_partner_classification_sync=True).write(values)

    @api.model_create_multi
    def create(self, vals_list):
        search_mode = self.env.context.get("res_partner_search_mode")
        has_studio_customer = "x_studio_es_cliente" in self._fields
        has_studio_supplier = "x_studio_es_proveedor" in self._fields

        for values in vals_list:
            if search_mode == "customer":
                values["is_customer"] = True
            elif "is_customer" not in values:
                if has_studio_customer and "x_studio_es_cliente" in values:
                    values["is_customer"] = bool(values["x_studio_es_cliente"])

            if search_mode == "supplier":
                values["is_supplier"] = True
            elif "is_supplier" not in values:
                if has_studio_supplier and "x_studio_es_proveedor" in values:
                    values["is_supplier"] = bool(values["x_studio_es_proveedor"])

        partners = super().create(vals_list)
        if not self.env.context.get("skip_partner_classification_sync"):
            categories = self._classification_categories()
            for partner, values in zip(partners, vals_list):
                classification_values = {}
                if (
                    "category_id" in values
                    and "is_customer" not in values
                    and "x_studio_es_cliente" not in values
                    and search_mode != "customer"
                ):
                    classification_values["is_customer"] = (
                        categories["customer"] in partner.category_id
                    )
                if (
                    "category_id" in values
                    and "is_supplier" not in values
                    and "x_studio_es_proveedor" not in values
                    and search_mode != "supplier"
                ):
                    classification_values["is_supplier"] = (
                        categories["supplier"] in partner.category_id
                    )
                if classification_values:
                    partner.with_context(
                        skip_partner_classification_sync=True
                    ).write(classification_values)
            partners._sync_classification()
        return partners

    def write(self, values):
        if self.env.context.get("skip_partner_classification_sync"):
            return super().write(values)

        values = dict(values)
        has_studio_customer = "x_studio_es_cliente" in self._fields
        has_studio_supplier = "x_studio_es_proveedor" in self._fields
        direct_customer_change = "is_customer" in values
        direct_supplier_change = "is_supplier" in values

        if (
            not direct_customer_change
            and has_studio_customer
            and "x_studio_es_cliente" in values
        ):
            values["is_customer"] = bool(values["x_studio_es_cliente"])
            direct_customer_change = True
        if (
            not direct_supplier_change
            and has_studio_supplier
            and "x_studio_es_proveedor" in values
        ):
            values["is_supplier"] = bool(values["x_studio_es_proveedor"])
            direct_supplier_change = True

        category_changed = "category_id" in values
        result = super().write(values)

        if category_changed and not (direct_customer_change and direct_supplier_change):
            categories = self._classification_categories()
            for partner in self:
                classification_values = {}
                if not direct_customer_change:
                    classification_values["is_customer"] = (
                        categories["customer"] in partner.category_id
                    )
                if not direct_supplier_change:
                    classification_values["is_supplier"] = (
                        categories["supplier"] in partner.category_id
                    )
                partner.with_context(skip_partner_classification_sync=True).write(
                    classification_values
                )

        relevant_fields = {
            "is_customer",
            "is_supplier",
            "x_studio_es_cliente",
            "x_studio_es_proveedor",
            "category_id",
        }
        if relevant_fields.intersection(values):
            self._sync_classification()
        return result

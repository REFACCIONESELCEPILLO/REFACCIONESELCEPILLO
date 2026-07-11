# -*- coding: utf-8 -*-

from odoo import models


class ShVehicleOEM(models.Model):
    _inherit = "sh.vehicle.oem"

    def ick_get_compatible_product(self):
        self.ensure_one()
        if not self.name:
            return self.env["product.template"]

        matching_variants = self.env["product.product"].sudo().search([
            ("default_code", "=", self.name),
        ])
        matching_templates = matching_variants.mapped("product_tmpl_id")
        if self.product_id:
            matching_templates -= self.product_id

        website = self.env["website"].get_current_website()
        if website:
            matching_templates = matching_templates.filtered_domain(
                website.sale_product_domain()
            )

        return matching_templates[:1]

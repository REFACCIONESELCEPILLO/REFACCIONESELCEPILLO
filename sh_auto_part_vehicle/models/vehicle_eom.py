# -*- coding: utf-8 -*-
# Part of Softhealer Technologies.
from odoo import models, fields


class ShVehicleOEM(models.Model):
    _name = "sh.vehicle.oem"
    _description = "Vehicle OEM"

    name = fields.Char('Code', required=True)
    brand_id = fields.Many2one(
        'motorcycle.brand',
        string="Marca",
    )
    is_visible_website = fields.Boolean('Is visible on website?')
    product_id = fields.Many2one('product.template', string='Product')
    company_id = fields.Many2one(
        'res.company',
        string='Company'
    )
    website_id = fields.Many2one(
        'website',
        string='Website'
    )

    def ickab_get_compatible_product(self):
        """Devuelve la pieza del catálogo que comparte el mismo código OEM."""
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


class ShProductSpecification(models.Model):
    _name = "sh.product.specification"
    _description = "Product Specification"

    name = fields.Char('Label', required=True)
    value = fields.Char('Value')
    product_id = fields.Many2one('product.template', string='Product')
    company_id = fields.Many2one(
        'res.company',
        string='Company'
    )
    website_id = fields.Many2one(
        'website',
        string='Website'
    )

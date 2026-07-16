# -*- coding: utf-8 -*-
# Part of Softhealer Technologies.
from odoo import api, models, fields


class ShVehicleOEM(models.Model):
    _name = "sh.vehicle.oem"
    _description = "Vehicle OEM"

    name = fields.Char('Code', required=True)
    supplier_id = fields.Many2one(
        'res.partner',
        string="Marca",
        domain="[('category_id', 'in', oem_brand_category_ids)]",
    )
    oem_brand_category_ids = fields.Many2many(
        'res.partner.category',
        compute='_compute_oem_brand_category_ids',
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

    @api.depends()
    def _compute_oem_brand_category_ids(self):
        category = self.env.ref(
            'sh_auto_part_vehicle.res_partner_category_oem_brand',
            raise_if_not_found=False,
        )
        for line in self:
            line.oem_brand_category_ids = category


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

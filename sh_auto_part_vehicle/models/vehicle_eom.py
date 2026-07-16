# -*- coding: utf-8 -*-
# Part of Softhealer Technologies.
from odoo import models, fields


class ShVehicleOEM(models.Model):
    _name = "sh.vehicle.oem"
    _description = "Vehicle OEM"

    name = fields.Char('Code', required=True)
    supplier_id = fields.Many2one(
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

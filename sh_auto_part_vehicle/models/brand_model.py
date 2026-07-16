# -*- coding: utf-8 -*-
# Part of Softhealer Technologies.
from odoo import fields, models


class MotorcycleBrand(models.Model):
    _name = "motorcycle.brand"
    _description = "Motorcycle Brand"
    _order = "sequence"

    name = fields.Char(required=True)
    sequence = fields.Integer(
        string=" "
    )
    company_id = fields.Many2one(
        'res.company',
        string='Company'
    )
    website_id = fields.Many2one(
        'website',
        string='Website'
    )

    def viewVehicleBrand(self,domain=None):
        return {
            'name': 'VehicleBrand',
            'type': 'ir.actions.act_window',
            'view_mode': 'list',
            'views': [(self.env.ref('sh_auto_part_vehicle.sh_motorcycle_brand_tree').id,'list')],
            'domain': domain or [],
            'res_model': 'motorcycle.brand',
            'context': dict(create=False),
            'target': 'current',


        }

# -*- coding: utf-8 -*-
# Part of Softhealer Technologies.
from odoo import api, fields, models


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

    @api.model_create_multi
    def create(self, vals_list):
        brands = super().create(vals_list)
        brands._ensure_brand_partner()
        return brands

    def write(self, vals):
        result = super().write(vals)
        if 'name' in vals:
            self._ensure_brand_partner()
        return result

    def _ensure_brand_partner(self):
        Partner = self.env['res.partner'].sudo()
        for brand in self:
            if not brand.name:
                continue
            partner = Partner.search([
                ('name', '=', brand.name),
            ], limit=1)
            if not partner:
                partner = Partner.create({
                    'name': brand.name,
                    'company_id': brand.company_id.id,
                })
            else:
                values = {}
                if partner.name != brand.name:
                    values['name'] = brand.name
                if values:
                    partner.write(values)
            partner._set_oem_brand_flag(True)




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

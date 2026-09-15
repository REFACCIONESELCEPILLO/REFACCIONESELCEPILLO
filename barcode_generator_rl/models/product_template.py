# -*- coding: utf-8 -*-
from odoo import fields, models, api, _
from odoo.exceptions import UserError


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    barcode_image = fields.Binary(
        string='Barcode Image',
        compute='_compute_barcode_image_from_variant',
        store=True,
        help='Imagen autogenerada del código de barras de la primera variante.',
    )

    @api.depends('product_variant_ids.barcode_image')
    def _compute_barcode_image_from_variant(self):
        for template in self:
            variant = template.product_variant_ids[:1]
            template.barcode_image = variant.barcode_image if variant else False

    def action_generate_configured_barcode(self):
        self.ensure_one()
        if self.product_variant_count != 1:
            raise UserError(_(
                'Este producto tiene múltiples variantes. Genere el barcode desde la variante específica.'
            ))
        variant = self.product_variant_ids[:1]
        if not variant:
            raise UserError(_('No se encontró una variante para este producto.'))
        return variant.action_generate_configured_barcode()

    def action_product_barcode_wizard(self):
        return {
            'name': _('Configure Product Barcode Generator'),
            'type': 'ir.actions.act_window',
            'res_model': 'product.barcode.generator.rl',
            'view_mode': 'form',
            'view_id': self.env.ref('barcode_generator_rl.product_barcode_wizard_rl_form_view').id,
            'target': 'new',
            'context': {
                'product_active_ids': self.ids,
                'active_model': self._name,
            },
        }

    def action_product_template_missing_image_generator_wizard(self):
        return {
            'name': _('Configure Missing Barcode Image Generator'),
            'type': 'ir.actions.act_window',
            'res_model': 'barcode.missing.image.generator.rl',
            'view_mode': 'form',
            'view_id': self.env.ref('barcode_generator_rl.product_barcode_missing_image_generator_view').id,
            'target': 'new',
            'context': {
                'product_active_ids': self.ids,
                'active_model': self._name,
            },
        }

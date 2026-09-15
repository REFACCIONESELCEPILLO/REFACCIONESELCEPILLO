# -*- coding: utf-8 -*-
import logging

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError, UserError

from .barcode_utils import BARCODE_SELECTION_MAP

_logger = logging.getLogger(__name__)


class ProductProduct(models.Model):
    _inherit = 'product.product'

    create_missing_image = fields.Boolean(
        string='Create Barcode image if missing',
        help='Create image if barcode number exists and image does not exist.',
    )
    barcode_image = fields.Binary(
        string='Barcode Image',
        help='Imagen autogenerada del código de barras del producto.',
    )
    barcode_generation_type_rl = fields.Selection(
        BARCODE_SELECTION_MAP, string='Tipo barcode generado', copy=False, readonly=True,
    )
    barcode_generation_config_id_rl = fields.Many2one(
        'barcode.generator.config.rl', string='Configuración de generación', copy=False, readonly=True,
        ondelete='set null',
    )
    barcode_generation_sequence_rl = fields.Char(
        string='Consecutivo de generación', copy=False, readonly=True,
    )
    barcode_generated_at_rl = fields.Datetime(
        string='Fecha de generación', copy=False, readonly=True,
    )

    @api.model_create_multi
    def create(self, vals_list):
        products = super().create(vals_list)
        if self.env.context.get('skip_auto_barcode_rl'):
            return products

        Config = self.env['barcode.generator.config.rl'].sudo()
        configs = {}
        for product in products.filtered(lambda p: not p.barcode):
            company = product.company_id or self.env.company
            if company.id not in configs:
                configs[company.id] = Config.search([
                    ('company_id', '=', company.id),
                    ('active', '=', True),
                    ('auto_generate_on_create', '=', True),
                ], limit=1)
            config = configs[company.id]
            if config:
                config.generate_for_product(product)
        return products

    def write(self, vals):
        vals = dict(vals)
        if 'barcode' in vals and 'barcode_image' not in vals:
            vals['barcode_image'] = False
        if 'barcode' in vals and not self.env.context.get('barcode_generator_internal_write_rl'):
            vals.update({
                'barcode_generation_type_rl': False,
                'barcode_generation_config_id_rl': False,
                'barcode_generation_sequence_rl': False,
                'barcode_generated_at_rl': False,
            })
        return super().write(vals)

    @api.constrains('barcode')
    def _check_barcode_unique_rl(self):
        for product in self.filtered('barcode'):
            duplicate = self.sudo().with_context(active_test=False).search([
                ('id', '!=', product.id),
                ('barcode', '=', product.barcode),
            ], limit=1)
            if duplicate:
                raise ValidationError(_(
                    'El código de barras %(barcode)s ya está asignado al producto %(product)s.'
                ) % {'barcode': product.barcode, 'product': duplicate.display_name})

    def _active_barcode_config_rl(self):
        self.ensure_one()
        company = self.company_id or self.env.company
        config = self.env['barcode.generator.config.rl'].sudo().search([
            ('company_id', '=', company.id),
            ('active', '=', True),
        ], limit=1)
        if not config:
            raise UserError(_(
                'No existe una Configuración Código de barras activa para %(company)s. '
                'Créela en Ajustes > Técnico > Configuración Código de barras.'
            ) % {'company': company.display_name})
        return config

    def action_generate_configured_barcode(self):
        self.ensure_one()
        if self.barcode:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('Código de barras'),
                    'message': _('El producto ya tiene el barcode %(barcode)s. No se modificó.') % {'barcode': self.barcode},
                    'type': 'warning',
                    'sticky': False,
                },
            }
        config = self._active_barcode_config_rl()
        code = config.generate_for_product(self)
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Código de barras generado'),
                'message': code,
                'type': 'success',
                'sticky': False,
                'next': {'type': 'ir.actions.client', 'tag': 'reload'},
            },
        }

    def action_product_variant_barcode_wizard(self):
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

    def action_product_variant_missing_image_generator_wizard(self):
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

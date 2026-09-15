# -*- coding: utf-8 -*-
import base64
import io
import logging
import barcode
from barcode.writer import ImageWriter
from odoo import api, fields, models, _
from odoo.exceptions import UserError

from ..models.barcode_utils import (
    BARCODE_SELECTION_MAP,
    BARCODE_TYPE_MAP,
    calculate_ean13_checksum,
    calculate_ean8_checksum,
    calculate_upca_checksum,
)

_logger = logging.getLogger(__name__)


class ProductBarcodeGeneratorRl(models.TransientModel):
    _name = 'product.barcode.generator.rl'
    _description = 'Product Barcode Generator'

    config_id = fields.Many2one('barcode.generator.config.rl', string='Configuración', readonly=True)
    barcode_type = fields.Selection(
        BARCODE_SELECTION_MAP,
        string='Barcode Type',
        required=True,
        default='code128',
        help=(
            'Code 128 es recomendado para códigos internos. EAN-13, UPC-A y EAN-8 '
            'aplican reglas de longitud y checksum. ISBN/ISSN se conservan por compatibilidad '
            'con el addon original y no usan la estructura empresarial automática.'
        ),
    )
    override_barcode = fields.Boolean(
        string='¿Sobrescribir barcodes existentes?',
        default=False,
        help='Sólo aplica a esta generación manual. La generación masiva nunca sobrescribe barcodes existentes.',
    )
    preview_code = fields.Char(string='Ejemplo', compute='_compute_preview')
    preview_image = fields.Binary(string='Previsualización', compute='_compute_preview')
    preview_message = fields.Char(string='Estado', compute='_compute_preview')

    @api.model
    def default_get(self, fields_list):
        vals = super().default_get(fields_list)
        company = self.env.company
        config = self.env['barcode.generator.config.rl'].sudo().search([
            ('company_id', '=', company.id), ('active', '=', True),
        ], limit=1)
        if config:
            vals['config_id'] = config.id
            vals['barcode_type'] = config.default_barcode_type
        return vals

    def _get_config(self):
        self.ensure_one()
        config = self.config_id
        if not config:
            config = self.env['barcode.generator.config.rl'].sudo().search([
                ('company_id', '=', self.env.company.id), ('active', '=', True),
            ], limit=1)
        if not config:
            raise UserError(_(
                'No existe una Configuración Código de barras activa. '
                'Créela en Ajustes > Técnico > Configuración Código de barras.'
            ))
        return config

    def _selected_products(self):
        active_model = self.env.context.get('active_model', '')
        product_ids = self.env.context.get('product_active_ids') or self.env.context.get('active_ids') or []
        if active_model == 'product.template':
            return self.env['product.template'].browse(product_ids).mapped('product_variant_ids')
        if active_model == 'product.product':
            return self.env['product.product'].browse(product_ids)
        return self.env['product.product']

    @api.depends('config_id', 'barcode_type')
    def _compute_preview(self):
        for wizard in self:
            wizard.preview_code = False
            wizard.preview_image = False
            wizard.preview_message = False
            try:
                config = wizard.config_id
                if not config:
                    wizard.preview_message = _('Primero configure una Configuración Código de barras activa.')
                    continue
                products = wizard._selected_products()
                product = products[:1]
                if not product:
                    wizard.preview_message = _('Seleccione al menos un producto para previsualizar.')
                    continue
                # ISBN/ISSN retain the legacy specialized generator and are not part
                # of the configurable company/category structure.
                if wizard.barcode_type in ('isbn', 'issn'):
                    code = wizard.generate_legacy_special_barcode(product, wizard.barcode_type)
                else:
                    code = config._compose_barcode(product.categ_id, 1, wizard.barcode_type, strict=True)
                wizard.preview_code = code
                wizard.preview_image = wizard._generate_barcode_image(code, wizard.barcode_type)
                wizard.preview_message = _('Ejemplo; no consume un consecutivo.')
            except Exception as exc:
                wizard.preview_message = str(exc)

    def action_generate_barcode(self):
        self.ensure_one()
        config = self._get_config()
        products = self._selected_products()
        if not products:
            raise UserError(_('Seleccione al menos un producto.'))

        generated = 0
        skipped = 0
        for product in products:
            if product.barcode and not self.override_barcode:
                skipped += 1
                continue
            if product.barcode and self.override_barcode:
                product.with_context(skip_auto_barcode_rl=True).write({'barcode': False})

            if self.barcode_type in ('isbn', 'issn'):
                # Specialized legacy formats do not participate in the company/category formula.
                code = self.generate_legacy_special_barcode(product, self.barcode_type)
                if self.env['product.product'].sudo().with_context(active_test=False).search_count([
                    ('barcode', '=', code), ('id', '!=', product.id),
                ]):
                    raise UserError(_('El código especializado %(code)s ya existe.') % {'code': code})
                image = self._generate_barcode_image(code, self.barcode_type)
                product.with_context(skip_auto_barcode_rl=True, barcode_generator_internal_write_rl=True).write({
                    'barcode': code,
                    'barcode_image': image,
                    'barcode_generation_type_rl': self.barcode_type,
                    'barcode_generated_at_rl': fields.Datetime.now(),
                })
            else:
                config.generate_for_product(product, barcode_type=self.barcode_type)
            generated += 1

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Generación de barcodes'),
                'message': _('%(generated)s generados; %(skipped)s conservados por tener barcode.') % {
                    'generated': generated, 'skipped': skipped,
                },
                'type': 'success',
                'sticky': False,
                'next': {'type': 'ir.actions.client', 'tag': 'reload'},
            },
        }

    def generate_legacy_special_barcode(self, product, barcode_type):
        """Compatibility generator for ISBN/ISSN from the original addon."""
        product_id = product.id
        if barcode_type == 'isbn':
            payload = '978' + str(product_id).zfill(9)[-9:]
            return payload + str(calculate_ean13_checksum(payload))
        if barcode_type == 'issn':
            # Keep the original addon concept: EAN-13 with 977 prefix.
            middle = str(product_id).zfill(7)[-7:] + '00'
            payload = '977' + middle
            return payload + str(calculate_ean13_checksum(payload))
        raise UserError(_('Tipo especializado no soportado.'))

    # Backward-compatible method name used by previous integrations.
    def generate_random_barcode(self, product):
        self.ensure_one()
        config = self._get_config()
        if self.barcode_type in ('isbn', 'issn'):
            return self.generate_legacy_special_barcode(product, self.barcode_type)
        # Preview-style value only; real assignment must use generate_for_product
        # so the global sequence is consumed safely.
        return config._compose_barcode(product.categ_id, 1, self.barcode_type, strict=True)

    def calculate_upca_checksum(self, code):
        return str(calculate_upca_checksum(code))

    def calculate_ean13_checksum(self, digits):
        return calculate_ean13_checksum(digits)

    def calculate_ean8_checksum(self, digits):
        return calculate_ean8_checksum(digits)

    @api.model
    def _generate_barcode_image(self, barcode_str, barcode_type='code128'):
        """Create a standards-aware barcode PNG and return base64 bytes."""
        if not barcode_str:
            return False
        try:
            value = str(barcode_str).strip()
            barcode_name = BARCODE_TYPE_MAP.get(barcode_type, 'code128')
            barcode_class = barcode.get_barcode_class(barcode_name)

            if barcode_type == 'ean13' or barcode_type == 'issn':
                if len(value) != 13 or not value.isdigit():
                    raise ValueError('EAN-13 requiere exactamente 13 dígitos.')
                expected = str(calculate_ean13_checksum(value[:12]))
                if value[-1] != expected:
                    raise ValueError('Checksum EAN-13 inválido.')
                barcode_obj = barcode_class(value[:12], writer=ImageWriter())
            elif barcode_type == 'isbn':
                if len(value) != 13 or not value.isdigit():
                    raise ValueError('ISBN-13 requiere exactamente 13 dígitos.')
                expected = str(calculate_ean13_checksum(value[:12]))
                if value[-1] != expected:
                    raise ValueError('Checksum ISBN-13 inválido.')
                barcode_obj = barcode_class(value[:12], writer=ImageWriter())
            elif barcode_type == 'ean8':
                if len(value) != 8 or not value.isdigit():
                    raise ValueError('EAN-8 requiere exactamente 8 dígitos.')
                expected = str(calculate_ean8_checksum(value[:7]))
                if value[-1] != expected:
                    raise ValueError('Checksum EAN-8 inválido.')
                barcode_obj = barcode_class(value[:7], writer=ImageWriter())
            elif barcode_type == 'upca':
                if len(value) != 12 or not value.isdigit():
                    raise ValueError('UPC-A requiere exactamente 12 dígitos.')
                expected = str(calculate_upca_checksum(value[:11]))
                if value[-1] != expected:
                    raise ValueError('Checksum UPC-A inválido.')
                barcode_obj = barcode_class(value[:11], writer=ImageWriter())
            elif barcode_type == 'code39':
                barcode_obj = barcode_class(value, writer=ImageWriter(), add_checksum=False)
            else:
                barcode_obj = barcode_class(value, writer=ImageWriter())

            image_stream = io.BytesIO()
            barcode_obj.write(image_stream, options={
                'write_text': True,
                'text_distance': 4.0,
                'center_text': True,
            })
            return base64.b64encode(image_stream.getvalue())
        except Exception as exc:
            _logger.warning('Error generating barcode image (%s / %s): %s', barcode_type, barcode_str, exc)
            return False



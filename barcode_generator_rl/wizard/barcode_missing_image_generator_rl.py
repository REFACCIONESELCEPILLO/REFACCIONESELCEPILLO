# -*- coding: utf-8 -*-
from odoo import fields, models

from ..models.barcode_utils import BARCODE_SELECTION_MAP


class BarcodeMissingImageGeneratorRl(models.TransientModel):
    _name = 'barcode.missing.image.generator.rl'
    _description = 'Barcode Missing Image Generator'

    barcode_type = fields.Selection(
        BARCODE_SELECTION_MAP,
        string='Barcode Type',
        default='code128',
        required=True,
        help=(
            'Seleccione el tipo real del barcode existente. Code 128 es la opción más segura '
            'cuando el valor es un identificador interno flexible. EAN/UPC requieren longitud '
            'y checksum válidos.'
        ),
    )

    def action_update_barcode_images(self):
        self.ensure_one()
        active_model = self.env.context.get('active_model', '')
        product_ids = self.env.context.get('product_active_ids', [])
        if active_model == 'product.template':
            products = self.env['product.template'].sudo().browse(product_ids).mapped('product_variant_ids')
        elif active_model == 'product.product':
            products = self.env['product.product'].sudo().browse(product_ids)
        else:
            products = self.env['product.product']

        generator = self.env['product.barcode.generator.rl'].sudo()
        for product in products:
            if product.barcode and not product.barcode_image:
                image_data = generator._generate_barcode_image(product.barcode, self.barcode_type)
                if image_data:
                    product.write({'barcode_image': image_data})

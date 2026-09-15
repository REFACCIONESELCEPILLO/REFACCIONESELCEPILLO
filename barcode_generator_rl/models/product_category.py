# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class ProductCategory(models.Model):
    _inherit = 'product.category'

    barcode_category_code = fields.Char(
        string='Código Barcode',
        size=2,
        copy=False,
        help=(
            'Código numérico de 2 dígitos usado por el generador estructurado. '
            'El valor 00 está reservado para representar un nivel de categoría inexistente.'
        ),
    )

    @api.constrains('barcode_category_code', 'parent_id')
    def _check_barcode_category_code(self):
        for category in self:
            code = (category.barcode_category_code or '').strip()
            if not code:
                continue
            if len(code) != 2 or not code.isdigit():
                raise ValidationError(_('El Código Barcode de categoría debe contener exactamente 2 dígitos.'))
            if code == '00':
                raise ValidationError(_('El código 00 está reservado para niveles de categoría inexistentes.'))
            duplicate = self.search([
                ('id', '!=', category.id),
                ('parent_id', '=', category.parent_id.id or False),
                ('barcode_category_code', '=', code),
            ], limit=1)
            if duplicate:
                raise ValidationError(_(
                    'El código %(code)s ya está utilizado por la categoría %(category)s dentro del mismo nivel.'
                ) % {'code': code, 'category': duplicate.complete_name})

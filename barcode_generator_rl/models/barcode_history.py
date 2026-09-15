# -*- coding: utf-8 -*-
from odoo import fields, models


class BarcodeGeneratedHistoryRl(models.Model):
    _name = 'barcode.generated.history.rl'
    _description = 'Historial de códigos de barras generados'
    _order = 'id desc'

    barcode = fields.Char(required=True, index=True, readonly=True)
    product_id = fields.Many2one('product.product', ondelete='set null', readonly=True, index=True)
    config_id = fields.Many2one('barcode.generator.config.rl', ondelete='set null', readonly=True, index=True)
    company_id = fields.Many2one('res.company', ondelete='set null', readonly=True, index=True)
    barcode_type = fields.Char(readonly=True)
    sequence_value = fields.Char(readonly=True)
    generated_at = fields.Datetime(default=fields.Datetime.now, readonly=True)

    _sql_constraints = [
        ('barcode_generated_history_unique', 'unique(barcode)', 'Este código de barras ya fue generado anteriormente.'),
    ]

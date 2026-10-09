# -*- coding: utf-8 -*-

from odoo import fields, models


class StockMove(models.Model):
    _inherit = "stock.move"

    ickab_brand_id = fields.Many2one(
        related="product_id.brand",
        string="Marca de autoparte",
        readonly=True,
    )


class StockMoveLine(models.Model):
    _inherit = "stock.move.line"

    ickab_brand_id = fields.Many2one(
        related="product_id.brand",
        string="Marca de autoparte",
        readonly=True,
    )

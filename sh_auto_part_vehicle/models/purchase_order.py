# -*- coding: utf-8 -*-

from odoo import fields, models


class PurchaseOrderLine(models.Model):
    _inherit = "purchase.order.line"

    ickab_brand_id = fields.Many2one(
        related="product_id.brand",
        string="Marca",
        readonly=True,
    )

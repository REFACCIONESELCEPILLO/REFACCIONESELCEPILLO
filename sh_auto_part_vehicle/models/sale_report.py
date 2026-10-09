# -*- coding: utf-8 -*-

from odoo import fields, models


class SaleReport(models.Model):
    _inherit = "sale.report"

    ickab_brand_id = fields.Many2one(
        "motorcycle.brand", string="Marca de autoparte", help="Marca",
    )

    def _select_additional_fields(self):
        res = super()._select_additional_fields()
        res["ickab_brand_id"] = "t.brand"
        return res

    def _group_by_sale(self):
        res = super()._group_by_sale()
        res += """,
            t.brand"""
        return res

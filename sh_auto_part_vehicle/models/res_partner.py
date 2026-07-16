# -*- coding: utf-8 -*-
# Part of Softhealer Technologies.
from odoo import api, fields, models


class ResPartner(models.Model):
    _inherit = "res.partner"

    is_oem_brand = fields.Boolean(
        string="esMarca",
        compute="_compute_is_oem_brand",
        inverse="_inverse_is_oem_brand",
        search="_search_is_oem_brand",
    )

    def _get_oem_brand_category(self):
        return self.env.ref(
            "sh_auto_part_vehicle.res_partner_category_oem_brand",
            raise_if_not_found=False,
        )

    @api.depends("category_id")
    def _compute_is_oem_brand(self):
        category = self._get_oem_brand_category()
        for partner in self:
            partner.is_oem_brand = bool(category and category in partner.category_id)

    def _inverse_is_oem_brand(self):
        category = self._get_oem_brand_category()
        if not category:
            return
        for partner in self:
            partner._set_oem_brand_flag(partner.is_oem_brand)

    def _search_is_oem_brand(self, operator, value):
        category = self._get_oem_brand_category()
        if operator not in ("=", "!="):
            return []
        is_enabled = bool(value)
        if operator == "!=":
            is_enabled = not is_enabled
        if not category:
            return [("id", "=", 0)] if is_enabled else []
        return [
            ("category_id", "in" if is_enabled else "not in", [category.id])
        ]

    def _set_oem_brand_flag(self, enabled=True):
        category = self._get_oem_brand_category()
        if not category:
            return
        command = (4, category.id) if enabled else (3, category.id)
        self.write({"category_id": [command]})

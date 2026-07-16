# -*- coding: utf-8 -*-
# Part of Softhealer Technologies.
from odoo import fields, models


class ResPartner(models.Model):
    _inherit = "res.partner"

    is_oem_brand = fields.Boolean(
        string="esMarca",
        default=False,
        index=True,
    )

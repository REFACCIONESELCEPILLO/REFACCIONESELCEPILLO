# -*- coding: utf-8 -*-
from odoo import fields, models


class PosConfig(models.Model):
    _inherit = "pos.config"

    ick_auto_show_card_stock = fields.Boolean(
        string="Disponibilidad en tarjetas", default=True)
    ick_auto_show_banner_stock = fields.Boolean(
        string="Disponibilidad en la franja del producto", default=True)
    ick_auto_show_oem = fields.Boolean(
        string="Códigos OEM", default=True)
    ick_auto_show_financials = fields.Boolean(
        string="Finanzas", default=True)
    ick_auto_show_order_totals = fields.Boolean(
        string="Totales de la orden", default=True)
    ick_auto_show_advertising = fields.Boolean(
        string="Publicidad en el escritorio", default=True)


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    pos_ick_auto_show_card_stock = fields.Boolean(
        related="pos_config_id.ick_auto_show_card_stock", readonly=False)
    pos_ick_auto_show_banner_stock = fields.Boolean(
        related="pos_config_id.ick_auto_show_banner_stock", readonly=False)
    pos_ick_auto_show_oem = fields.Boolean(
        related="pos_config_id.ick_auto_show_oem", readonly=False)
    pos_ick_auto_show_financials = fields.Boolean(
        related="pos_config_id.ick_auto_show_financials", readonly=False)
    pos_ick_auto_show_order_totals = fields.Boolean(
        related="pos_config_id.ick_auto_show_order_totals", readonly=False)
    pos_ick_auto_show_advertising = fields.Boolean(
        related="pos_config_id.ick_auto_show_advertising", readonly=False)

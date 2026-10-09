# -*- coding: utf-8 -*-
# Part of Softhealer Technologies.


from odoo import fields, models


class Website(models.Model):
    _inherit = 'website'

    sh_is_show_garage = fields.Boolean("Garage Feature?", default=True)
    sh_do_not_consider_vehicle_over_category = fields.Boolean(
        "Do not consider vehicle when click on category")
    sh_do_not_consider_vehicle_over_attribute = fields.Boolean(
        "Do not consider vehicle when click on attributes")
    sh_do_not_consider_vehicle_over_price = fields.Boolean(
        "Do not consider vehicle when change on min/max price")


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    sh_is_show_garage = fields.Boolean(
        related="website_id.sh_is_show_garage",
        string="Garage Feature?",
        readonly=False,
    )
    sh_do_not_consider_vehicle_over_category = fields.Boolean(
        related="website_id.sh_do_not_consider_vehicle_over_category",
        string="Do not consider vehicle when click on category",
        readonly=False,
    )
    sh_do_not_consider_vehicle_over_attribute = fields.Boolean(
        related="website_id.sh_do_not_consider_vehicle_over_attribute",
        string="Do not consider vehicle when click on attributes",
        readonly=False,
    )
    sh_do_not_consider_vehicle_over_price = fields.Boolean(
        related="website_id.sh_do_not_consider_vehicle_over_price",
        string="Do not consider vehicle when change on min/max price",
        readonly=False,
    )

    # Ajustes del punto de venta (identificación, catálogo y recibo).
    pos_ickab_product_label_mode = fields.Selection(
        related="pos_config_id.ickab_pos_product_label_mode",
        readonly=False,
    )
    pos_ickab_catalog_card_width = fields.Integer(
        related="pos_config_id.ickab_catalog_card_width", readonly=False)
    pos_ickab_catalog_image_height = fields.Integer(
        related="pos_config_id.ickab_catalog_image_height", readonly=False)
    pos_ickab_catalog_image_fit = fields.Selection(
        related="pos_config_id.ickab_catalog_image_fit", readonly=False)
    pos_ickab_catalog_font_size = fields.Integer(
        related="pos_config_id.ickab_catalog_font_size", readonly=False)
    pos_ickab_catalog_name_lines = fields.Integer(
        related="pos_config_id.ickab_catalog_name_lines", readonly=False)
    pos_ickab_catalog_show_price = fields.Boolean(
        related="pos_config_id.ickab_catalog_show_price", readonly=False)
    pos_ickab_receipt_paper_width = fields.Selection(
        related="pos_config_id.ickab_receipt_paper_width", readonly=False)
    pos_ickab_receipt_font_size = fields.Integer(
        related="pos_config_id.ickab_receipt_font_size", readonly=False)
    pos_ickab_receipt_line_height = fields.Selection(
        related="pos_config_id.ickab_receipt_line_height", readonly=False)
    pos_ickab_receipt_logo_height = fields.Integer(
        related="pos_config_id.ickab_receipt_logo_height", readonly=False)

from odoo import fields, models


class PosConfig(models.Model):
    _inherit = "pos.config"

    ickab_catalog_card_width = fields.Integer(string="Ancho mínimo de tarjeta (px)", default=120)
    ickab_catalog_image_height = fields.Integer(string="Alto de imagen (px)", default=96)
    ickab_catalog_image_fit = fields.Selection(
        [("contain", "Mostrar completa"), ("cover", "Llenar y recortar")],
        string="Ajuste de imagen", default="contain", required=True,
    )
    ickab_catalog_font_size = fields.Integer(string="Tamaño del nombre (px)", default=14)
    ickab_catalog_name_lines = fields.Integer(string="Cantidad de líneas del nombre", default=3)
    ickab_catalog_show_price = fields.Boolean(string="Mostrar precio", default=False)
    ickab_receipt_paper_width = fields.Selection(
        [("58", "58 mm"), ("80", "80 mm")],
        string="Ancho del recibo (mm)", default="80", required=True,
    )
    ickab_receipt_font_size = fields.Integer(string="Tamaño de texto del recibo (px)", default=12)
    ickab_receipt_line_height = fields.Selection(
        [("compact", "Compacto"), ("normal", "Normal")],
        string="Espaciado del recibo", default="normal", required=True,
    )
    ickab_receipt_logo_height = fields.Integer(string="Alto máximo del logotipo (px)", default=80)


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    pos_ickab_catalog_card_width = fields.Integer(related="pos_config_id.ickab_catalog_card_width", readonly=False)
    pos_ickab_catalog_image_height = fields.Integer(related="pos_config_id.ickab_catalog_image_height", readonly=False)
    pos_ickab_catalog_image_fit = fields.Selection(related="pos_config_id.ickab_catalog_image_fit", readonly=False)
    pos_ickab_catalog_font_size = fields.Integer(related="pos_config_id.ickab_catalog_font_size", readonly=False)
    pos_ickab_catalog_name_lines = fields.Integer(related="pos_config_id.ickab_catalog_name_lines", readonly=False)
    pos_ickab_catalog_show_price = fields.Boolean(related="pos_config_id.ickab_catalog_show_price", readonly=False)
    pos_ickab_receipt_paper_width = fields.Selection(related="pos_config_id.ickab_receipt_paper_width", readonly=False)
    pos_ickab_receipt_font_size = fields.Integer(related="pos_config_id.ickab_receipt_font_size", readonly=False)
    pos_ickab_receipt_line_height = fields.Selection(related="pos_config_id.ickab_receipt_line_height", readonly=False)
    pos_ickab_receipt_logo_height = fields.Integer(related="pos_config_id.ickab_receipt_logo_height", readonly=False)

from odoo import fields, models


class PosConfig(models.Model):
    _inherit = "pos.config"

    product_label_mode = fields.Selection(
        related="ickab_pos_product_label_mode",
        string="Identificación del producto en POS",
        readonly=False,
    )


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    pos_product_label_mode = fields.Selection(
        related="pos_config_id.product_label_mode",
        readonly=False,
    )

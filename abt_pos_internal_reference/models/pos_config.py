from odoo import fields, models


class PosConfig(models.Model):
    _inherit = "pos.config"

    product_label_mode = fields.Selection(
        selection=[
            ("reference", "Referencia interna"),
            ("name", "Nombre"),
            ("both", "Ambos"),
        ],
        string="Identificación del producto en POS",
        default="both",
        required=True,
    )


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    pos_product_label_mode = fields.Selection(
        related="pos_config_id.product_label_mode",
        readonly=False,
    )

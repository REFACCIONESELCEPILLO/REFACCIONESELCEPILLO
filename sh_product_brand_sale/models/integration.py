from odoo import api, fields, models


class ProductProduct(models.Model):
    _inherit = "product.product"

    brand_name = fields.Char(
        related="brand.name",
        string="Nombre de la marca",
        readonly=True,
    )

    @api.model
    def _load_pos_data_fields(self, config_id):
        fields_to_load = super()._load_pos_data_fields(config_id)
        return list(dict.fromkeys([*fields_to_load, "brand", "brand_name"]))


class SaleOrderLine(models.Model):
    _inherit = "sale.order.line"

    brand_id = fields.Many2one(
        related="product_id.brand", string="Marca", readonly=True
    )


class PurchaseOrderLine(models.Model):
    _inherit = "purchase.order.line"

    brand_id = fields.Many2one(
        related="product_id.brand", string="Marca", readonly=True
    )


class StockMove(models.Model):
    _inherit = "stock.move"

    brand_id = fields.Many2one(
        related="product_id.brand", string="Marca", readonly=True
    )


class StockMoveLine(models.Model):
    _inherit = "stock.move.line"

    brand_id = fields.Many2one(
        related="product_id.brand", string="Marca", readonly=True
    )

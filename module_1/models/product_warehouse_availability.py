# -*- coding: utf-8 -*-

from odoo import fields, models, tools


class ProductWarehouseAvailability(models.Model):
    _name = 'product.warehouse.availability'
    _description = 'Disponibilidad libre por almacen'
    _auto = False
    _rec_name = 'product_id'
    _order = 'warehouse_id, product_id'

    product_id = fields.Many2one('product.product', string='Producto', readonly=True)
    product_tmpl_id = fields.Many2one('product.template', string='Plantilla de producto', readonly=True)
    product_uom_id = fields.Many2one('uom.uom', string='UdM', readonly=True)
    warehouse_id = fields.Many2one('stock.warehouse', string='Almacen', readonly=True)
    warehouse_name = fields.Char(string='Nombre almacen', readonly=True)
    company_id = fields.Many2one('res.company', string='Compania', readonly=True)
    quantity_on_hand = fields.Float(string='Fisico', readonly=True)
    reserved_quantity = fields.Float(string='Reservado', readonly=True)
    free_quantity = fields.Float(string='Disponible', readonly=True)

    def init(self):
        tools.drop_view_if_exists(self.env.cr, self._table)
        self.env.cr.execute("""
            CREATE OR REPLACE VIEW product_warehouse_availability AS (
                SELECT
                    MIN(sq.id) AS id,
                    sq.product_id AS product_id,
                    pp.product_tmpl_id AS product_tmpl_id,
                    pt.uom_id AS product_uom_id,
                    sw.id AS warehouse_id,
                    sw.name AS warehouse_name,
                    COALESCE(sq.company_id, sw.company_id) AS company_id,
                    SUM(sq.quantity) AS quantity_on_hand,
                    SUM(sq.reserved_quantity) AS reserved_quantity,
                    SUM(sq.quantity - sq.reserved_quantity) AS free_quantity
                FROM stock_quant sq
                    JOIN product_product pp ON pp.id = sq.product_id
                    JOIN product_template pt ON pt.id = pp.product_tmpl_id
                    JOIN stock_location sl ON sl.id = sq.location_id
                    JOIN stock_warehouse sw ON (sq.company_id IS NULL OR sw.company_id = sq.company_id)
                    JOIN stock_location wh_view ON wh_view.id = sw.view_location_id
                WHERE
                    sl.usage = 'internal'
                    AND sl.parent_path LIKE wh_view.parent_path || '%%'
                GROUP BY
                    sq.product_id,
                    pp.product_tmpl_id,
                    pt.uom_id,
                    sw.id,
                    sw.name,
                    COALESCE(sq.company_id, sw.company_id)
            )
        """)

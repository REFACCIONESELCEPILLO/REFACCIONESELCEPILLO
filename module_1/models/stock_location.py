# -*- coding: utf-8 -*-
from odoo import fields, models


class StockLocation(models.Model):
    _inherit = 'stock.location'

    branch = fields.Selection(
        selection=[
            ('MAN', 'Manantial'),
            ('MAG', 'Magon'),
            ('POZ', 'Poza Rica'),
            ('PAP', 'Papantla'),
            ('TUX', 'Tuxpan'),
        ],
        string='Sucursal',
    )

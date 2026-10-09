# -*- coding: utf-8 -*-
################################################################################
#
#    Cybrosys Technologies Pvt. Ltd.
#    Copyright (C) 2024-TODAY Cybrosys Technologies(<https://www.cybrosys.com>).
#    Author: Adarsh K (odoo@cybrosys.com)
#
#    This program is free software: you can modify
#    it under the terms of the GNU Affero General Public License (AGPL) as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <https://www.gnu.org/licenses/>.
#
################################################################################
{
    'name': 'SH Product Brand in Sale',
    'version': '18.0.3.0.3',
    'category': 'Inventory/Inventory',
    'summary': 'Use auto-part brands across products, sales, purchases, inventory and POS',
    'description': 'Extends the brand catalog provided by sh_auto_part_vehicle '
                   'across Odoo business flows.',
    'author': 'Cybrosys Techno Solutions',
    'company': 'Cybrosys Techno Solutions',
    'maintainer': 'Cybrosys Techno Solutions',
    'website': 'https://www.cybrosys.com',
    'depends': [
        'sale_management',
        'purchase',
        'stock',
        'point_of_sale',
        'sh_auto_part_vehicle',
    ],
    'data': [
        'views/product_brand_views.xml',
        'views/product_template_views.xml',
        'views/sale_report_views.xml',
        'views/product_brand_integration_views.xml',
    ],
    'assets': {
        'point_of_sale._assets_pos': [
            'sh_product_brand_sale/static/src/pos/product_brand_pos.js',
            'sh_product_brand_sale/static/src/pos/product_brand_pos.xml',
            'sh_product_brand_sale/static/src/pos/product_brand_pos.scss',
        ],
    },
    'images': ['static/description/banner.png'],
    'license': 'AGPL-3',
    'installable': True,
    'auto_install': False,
    'application': False,
}

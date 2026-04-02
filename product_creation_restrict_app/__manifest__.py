# -*- coding: utf-8 -*-
{
    'name' : 'Product Creation Restriction App',
    'author': "Edge Technologies",
    'version' : '18.0',
    'live_test_url':'https://youtu.be/2RZ10tISRDY',
    "images":['static/description/main_screenshot.png'],
    'summary' : 'Product creation restrict product creation disable quick product creation disable product create restriction product creation restriction product creation restriction on product creation disable create product option',
     'description' : """
         Product creation restrict app
    """,
    "license" : "OPL-1",
    'depends' : ['base', 'sale_management', 'account', 'purchase', 'stock', 'mrp'],
    'data': [
            'views/sale_views.xml',
            'views/purchase_views.xml',
            'views/stock_views.xml',
            'views/account_move_views.xml',
            'views/mrp_production_views.xml',
            ],
    'qweb' : [],
    'demo' : [],
    'installable' : True,
    'auto_install' : False,
    'price': 5,
    'currency': "EUR",
    'category' : 'Sales',
}

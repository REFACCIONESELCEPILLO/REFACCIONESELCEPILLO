# -*- coding: utf-8 -*-
{
    "name": "ICKAB Advanced Audit & Login History",
    "summary": "Odoo 18 login history, session monitoring and configurable user activity audit",

    "description": """
ICKAB Advanced Audit & Login History
====================================

Overview
--------
ICKAB Advanced Audit & Login History is an Odoo 18 administration module for
monitoring successful and failed logins, logout history, session details,
browser/device information, IP address and geolocation.

User activity auditing is controlled from Model Log Configuration. Only active
configured models and the enabled operations (Create, Modify and Delete) are
audited. Related line models can be included for Sales, Purchases, Invoices and
Stock Pickings.

Main Features
-------------
- Login and logout history
- Failed login tracking
- Session duration and active session visibility
- Browser, operating system, IP and location information
- Dashboard for login activity
- Configurable create/modify/delete audit by Odoo model
- Old/new field value tracking
- Related line tracking for Sale Orders, Purchase Orders, Invoices and Pickings
- Permission-controlled audit access
- User session visibility and Kill All Sessions action
- Spanish (Mexico) translation included

ICKAB Edition
-------------
This edition is maintained and modified by ICKAB for Odoo 18.
Website: https://ickab.mx

Legal Notice
------------
This edition contains modifications to software originally distributed under
LGPL-3. Original third-party rights remain with their respective holders.
Modifications, redesign, translations and additional functionality in this
edition are maintained by ICKAB.
""",

    "author": "ICKAB",
    "website": "https://ickab.mx",
    "maintainer": "ICKAB",

    "category": "Administration",
    "version": "18.0.1.2.0",
    "license": "LGPL-3",

    "depends": [
        "base",
        "web",
    ],

    "data": [
        "security/audit_security.xml",
        "security/ir.model.access.csv",
        "views/login_history_views.xml",
        "views/user_activity_audit_views.xml",
        "views/activity_log_config_views.xml",
        "views/login_history_dashboard_menu.xml",
    ],

    "assets": {
        "web.assets_backend": [
            "mst_advanced_login_history/static/src/js/session_tracker.js",
            "mst_advanced_login_history/static/src/js/login_history_dashboard.js",
            "mst_advanced_login_history/static/src/xml/login_history_dashboard.xml",
            "mst_advanced_login_history/static/src/scss/login_history_dashboard.scss",
        ],
        "web.assets_frontend": [
            "mst_advanced_login_history/static/src/js/login_location.js",
        ],
    },

    "images": [],

    "installable": True,
    "application": True,
    "auto_install": False,
}

# -*- coding: utf-8 -*-
"""Compatibility cleanup executed before installing the warehouse module."""


def pre_init_hook(env):
    """Disable product views that still reference an obsolete OEM field.

    Older versions of ``sh_auto_part_vehicle`` stored
    ``oem_brand_category_ids`` in a product-template view. The field was
    removed later, so Odoo cannot validate any new inherited product view
    until this obsolete reference is removed from the database.
    """
    env.cr.execute(
        """
        UPDATE ir_ui_view
           SET active = FALSE
         WHERE model = 'product.template'
           AND arch_db::text LIKE %s
        """,
        ("%oem_brand_category_ids%",),
    )

# -*- coding: utf-8 -*-
"""Compatibility cleanup executed before installing the warehouse module."""


def pre_init_hook(env):
    """Remove an obsolete OEM helper field from persisted product views.

    Older versions of ``sh_auto_part_vehicle`` stored
    ``oem_brand_category_ids`` in a product-template view. The field was
    removed later, so Odoo cannot validate any new inherited product view
    until this obsolete reference is removed from the database.
    """
    env.cr.execute(
        """
        UPDATE ir_ui_view
           SET arch_db = replace(
               replace(
                   arch_db,
                   '<field name="oem_brand_category_ids" column_invisible="1"/>',
                   ''
               ),
               ' domain="[(\'category_id\', \'in\', oem_brand_category_ids)]"',
               ''
           )
         WHERE model = 'product.template'
           AND arch_db LIKE '%oem_brand_category_ids%'
        """
    )

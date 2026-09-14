# -*- coding: utf-8 -*-


def migrate(cr, version):
    """Apply validated 4B-2054L capabilities to databases upgraded from 3.x.

    Compatibility seed records are noupdate by design so administrators can
    maintain them. This one-time upgrade only initializes the capabilities that
    were physically validated before 4.0 was released.
    """
    cr.execute("""
        UPDATE ickab_print_compatibility_profile AS profile
           SET label_direction = '1',
               tspl_bitmap_one_is_black = FALSE,
               supports_inline_bitmap = TRUE,
               tspl_scalable_font0 = TRUE
         WHERE profile.id = (
             SELECT res_id
               FROM ir_model_data
              WHERE module = 'ickab_direct_print'
                AND name = 'compat_4barcode_4b2054l'
                AND model = 'ickab.print.compatibility.profile'
              LIMIT 1
         )
    """)

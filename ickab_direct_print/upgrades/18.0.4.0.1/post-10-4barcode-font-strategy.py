# -*- coding: utf-8 -*-


def migrate(cr, version):
    """Use the physically validated fixed resident fonts on 4B-2054L.

    Earlier 4.0.0 marked TSPL2 font 0 as available based on protocol support.
    The 1/3/10-label physical acceptance run showed that its rendered physical
    scale is not reliable enough on the tested 4B-2054L firmware.  Keep the
    renderer generic and correct the device capability in the profile instead.
    """
    cr.execute("""
        UPDATE ickab_print_compatibility_profile AS profile
           SET tspl_scalable_font0 = FALSE
         WHERE profile.id = (
             SELECT res_id
               FROM ir_model_data
              WHERE module = 'ickab_direct_print'
                AND name = 'compat_4barcode_4b2054l'
                AND model = 'ickab.print.compatibility.profile'
              LIMIT 1
         )
    """)

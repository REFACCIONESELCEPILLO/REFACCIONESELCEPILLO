# Copyright 2026 ICKAB. All rights reserved.

def migrate(cr, version):
    # 18.0.1.x did not have technical_key. Odoo has created the column before
    # this post phase; populate only missing values and preserve every design.
    cr.execute("""
        UPDATE ickab_label_template
           SET technical_key = md5(id::text || ':' || clock_timestamp()::text || ':' || random()::text)
         WHERE technical_key IS NULL OR technical_key = ''
    """)

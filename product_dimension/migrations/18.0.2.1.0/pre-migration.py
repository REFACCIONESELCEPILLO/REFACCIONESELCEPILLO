def migrate(cr, version):
    """Move existing per-template component mappings to attribute values."""
    cr.execute("""
        ALTER TABLE product_attribute_value
        ADD COLUMN IF NOT EXISTS component_product_id integer
    """)
    cr.execute("""
        ALTER TABLE product_attribute_value
        ADD COLUMN IF NOT EXISTS skip_component boolean DEFAULT FALSE
    """)
    cr.execute("""
        ALTER TABLE product_attribute_value
        ADD COLUMN IF NOT EXISTS component_calculation varchar DEFAULT 'attribute'
    """)
    cr.execute("""
        ALTER TABLE product_attribute_value
        ADD COLUMN IF NOT EXISTS component_qty_factor double precision DEFAULT 1.0
    """)
    cr.execute("""
        WITH legacy_mapping AS (
            SELECT DISTINCT ON (product_attribute_value_id)
                   product_attribute_value_id,
                   component_product_id,
                   COALESCE(skip_component, FALSE) AS skip_component,
                   COALESCE(component_calculation, 'attribute') AS component_calculation,
                   COALESCE(component_qty_factor, 1.0) AS component_qty_factor
              FROM product_template_attribute_value
             WHERE component_product_id IS NOT NULL
                OR skip_component IS TRUE
             ORDER BY product_attribute_value_id,
                      (component_product_id IS NOT NULL) DESC,
                      skip_component DESC,
                      id
        )
        UPDATE product_attribute_value AS pav
           SET component_product_id = legacy.component_product_id,
               skip_component = legacy.skip_component,
               component_calculation = legacy.component_calculation,
               component_qty_factor = legacy.component_qty_factor
          FROM legacy_mapping AS legacy
         WHERE pav.id = legacy.product_attribute_value_id
           AND pav.component_product_id IS NULL
           AND pav.skip_component IS NOT TRUE
    """)

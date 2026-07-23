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
                   (to_jsonb(ptav)->>'component_product_id')::integer
                       AS component_product_id,
                   COALESCE(
                       (to_jsonb(ptav)->>'skip_component')::boolean,
                       FALSE
                   ) AS skip_component,
                   COALESCE(
                       to_jsonb(ptav)->>'component_calculation',
                       'attribute'
                   ) AS component_calculation,
                   COALESCE(
                       (to_jsonb(ptav)->>'component_qty_factor')::double precision,
                       1.0
                   ) AS component_qty_factor
              FROM product_template_attribute_value AS ptav
             WHERE (to_jsonb(ptav)->>'component_product_id')::integer IS NOT NULL
                OR COALESCE(
                       (to_jsonb(ptav)->>'skip_component')::boolean,
                       FALSE
                   ) IS TRUE
             ORDER BY product_attribute_value_id,
                      (
                          (to_jsonb(ptav)->>'component_product_id')::integer
                          IS NOT NULL
                      ) DESC,
                      COALESCE(
                          (to_jsonb(ptav)->>'skip_component')::boolean,
                          FALSE
                      ) DESC,
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

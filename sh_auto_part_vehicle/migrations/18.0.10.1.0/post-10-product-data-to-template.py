"""Move automotive product data from variants to their template."""


def _copy_many2many(cr, source_table, source_product_column,
                    source_value_column, target_table, target_value_column):
    cr.execute(
        f"""
        INSERT INTO {target_table} (product_tmpl_id, {target_value_column})
        SELECT DISTINCT product.product_tmpl_id, source.{source_value_column}
          FROM {source_table} AS source
          JOIN product_product AS product
            ON product.id = source.{source_product_column}
         WHERE NOT EXISTS (
               SELECT 1
                 FROM {target_table} AS target
                WHERE target.product_tmpl_id = product.product_tmpl_id
                  AND target.{target_value_column} = source.{source_value_column}
         )
        """
    )


def migrate(cr, version):
    # Preserve every M2M value. For historical variants with different scalar
    # values, choose the first populated value in a deterministic way.
    cr.execute(
        """
        UPDATE product_template AS template
           SET sh_is_common_product = values.sh_is_common_product,
               brand = COALESCE(template.brand, values.brand),
               made_in = COALESCE(template.made_in, values.made_in)
          FROM (
                SELECT product_tmpl_id,
                       BOOL_OR(COALESCE(sh_is_common_product, FALSE))
                           AS sh_is_common_product,
                       (ARRAY_AGG(brand ORDER BY id)
                           FILTER (WHERE brand IS NOT NULL))[1] AS brand,
                       (ARRAY_AGG(made_in ORDER BY id)
                           FILTER (WHERE made_in IS NOT NULL))[1] AS made_in
                  FROM product_product
              GROUP BY product_tmpl_id
          ) AS values
         WHERE values.product_tmpl_id = template.id
        """
    )

    relations = (
        ("motorcycle_garde_product_product_rel", "product_product_id", "motorcycle_garde_id",
         "motorcycle_garde_product_template_rel", "motorcycle_garde_id"),
        ("motorcycle_engine_product_product_rel", "product_product_id", "motorcycle_engine_id",
         "motorcycle_engine_product_template_rel", "motorcycle_engine_id"),
        ("motorcycle_product_type_product_product_rel", "product_product_id", "motorcycle_product_type_id",
         "motorcycle_product_type_product_template_rel", "motorcycle_product_type_id"),
        ("motorcycle_transmission_product_product_rel", "product_product_id", "motorcycle_transmission_id",
         "motorcycle_transmission_product_template_rel", "motorcycle_transmission_id"),
        ("product_product_motorcycle_motorcycle_rel", "product_id", "motorcycle_id",
         "product_template_motorcycle_motorcycle_rel", "motorcycle_id"),
    )
    for relation in relations:
        _copy_many2many(cr, *relation)

DO $$
BEGIN
    IF EXISTS (
        SELECT 1 FROM ir_module_module WHERE name = 'product_brand_sale'
    ) AND EXISTS (
        SELECT 1 FROM ir_module_module WHERE name = 'sh_product_brand_sale'
    ) THEN
        RAISE EXCEPTION
            'Both product_brand_sale and sh_product_brand_sale exist in ir_module_module';
    ELSIF EXISTS (
        SELECT 1 FROM ir_module_module WHERE name = 'product_brand_sale'
    ) THEN
        UPDATE ir_module_module
           SET name = 'sh_product_brand_sale'
         WHERE name = 'product_brand_sale';
    END IF;
END
$$;

UPDATE ir_model_data
   SET module = 'sh_product_brand_sale'
 WHERE module = 'product_brand_sale';

UPDATE ir_model_data
   SET name = 'module_sh_product_brand_sale'
 WHERE module = 'base'
   AND name = 'module_product_brand_sale'
   AND NOT EXISTS (
       SELECT 1
         FROM ir_model_data
        WHERE module = 'base'
          AND name = 'module_sh_product_brand_sale'
   );

UPDATE ir_module_module_dependency
   SET name = 'sh_product_brand_sale'
 WHERE name = 'product_brand_sale';

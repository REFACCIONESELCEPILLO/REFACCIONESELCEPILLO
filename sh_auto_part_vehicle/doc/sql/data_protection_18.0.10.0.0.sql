-- ============================================================================
--  ICKAB · sh_auto_part_vehicle · Protección de datos · 18.0.10.0.0
-- ----------------------------------------------------------------------------
--  NO es un script de migración de Odoo. No hay carpeta ``migrations/`` ni
--  hooks ``pre-migrate``/``post-migrate``. Es una salvaguarda de datos a nivel
--  de base de datos que se ejecuta UNA sola vez, con el servicio
--  ``odoo18-elcepillo.service`` DETENIDO, ANTES de desinstalar los módulos de
--  origen y ANTES de actualizar el componente consolidado.
--
--  Objetivo
--  --------
--   * Conservar TODO el catálogo del componente base (marcas, makes, models,
--     years, tipos, garaje, OEM, etc.) renombrando el módulo base
--     ``sh_auto_part_vehicle`` -> ``sh_auto_part_vehicle`` (continuidad:
--     Odoo lo trata como el mismo módulo; no se pierde ninguna tabla).
--   * Conservar los ajustes de POS (``pos.config``) absorbidos desde los
--     submódulos ``abt_pos_internal_reference`` e ``ickab_pos_product_catalog``,
--     reasignando la propiedad de sus campos al módulo consolidado para que la
--     desinstalación de los submódulos NO ejecute ``ALTER TABLE ... DROP COLUMN``
--     (ver ``ir_model_fields._drop_column`` en el core de Odoo 18).
--   * Renombrar ``pos.config.product_label_mode`` ->
--     ``ickab_pos_product_label_mode`` conservando el valor de cada POS.
--
--  Requisitos previos
--  ------------------
--   1. Detener el servicio:   systemctl stop odoo18-elcepillo.service
--   2. Backup de BD y filestore.
--
--  Uso
--  ---
--   psql -h 127.0.0.1 -U odoo_elcepillo -d db_elcepillo \
--        -f doc/sql/data_protection_18.0.10.0.0.sql
--
--  Tras ejecutar este script (siempre con el servicio detenido):
--   /opt/odoo18/elcepillo/venv/bin/python /opt/odoo18/odoo/odoo-bin \
--     -c /opt/odoo18/elcepillo/config/odoo18.conf \
--     -d db_elcepillo -u sh_auto_part_vehicle --stop-after-init
--   (ese arranque actualiza el componente y, además, desinstala los 4 módulos
--    de origen que este script deja marcados como 'to remove').
--
--  Nota: se usa ``-u`` (no ``-i``) porque el módulo consolidado queda como la
--  continuación del base ya "instalado" tras el renombrado.
-- ============================================================================

BEGIN;

-- ----------------------------------------------------------------------------
-- 1) Continuidad del módulo base
--    sh_auto_part_vehicle (18.0.9.x)  ->  sh_auto_part_vehicle
-- ----------------------------------------------------------------------------
UPDATE ir_module_module
   SET name = 'sh_auto_part_vehicle'
 WHERE name = 'sh_auto_part_vehicle';

-- Toda la propiedad de datos del base (330+ registros: modelos, campos, vistas,
-- acciones, grupos, plantillas, etc.) viaja con el módulo renombrado.
UPDATE ir_model_data
   SET module = 'sh_auto_part_vehicle'
 WHERE module = 'sh_auto_part_vehicle';

-- XML id del propio módulo (base.module_<name>).
UPDATE ir_model_data
   SET name = 'module_sh_auto_part_vehicle'
 WHERE module = 'base'
   AND model = 'ir.module.module'
   AND name = 'module_sh_auto_part_vehicle';

-- Dependencias declaradas por módulos que PERMANECEN instalados
-- (sh_auto_part_vehicle_labels, elcepillo_auto_sale, ...).
UPDATE ir_module_module_dependency
   SET name = 'sh_auto_part_vehicle'
 WHERE name = 'sh_auto_part_vehicle';

-- ----------------------------------------------------------------------------
-- 2) Protección de los ajustes de POS (pos.config)
--    Reasignar la propiedad de los campos de pos.config absorbidos desde los
--    submódulos al módulo consolidado. Así, al desinstalar los submódulos,
--    dichos campos no se eliminan y sus columnas (con datos) se conservan.
-- ----------------------------------------------------------------------------
UPDATE ir_model_data d
   SET module = 'sh_auto_part_vehicle'
  FROM ir_model_fields f
 WHERE d.model = 'ir.model.fields'
   AND d.res_id = f.id
   AND d.module IN ('abt_pos_internal_reference', 'ickab_pos_product_catalog')
   AND f.model = 'pos.config';

-- ----------------------------------------------------------------------------
-- 3) Renombrar la identificación del producto en POS
--    product_label_mode -> ickab_pos_product_label_mode
--    (campo + xmlid + columna de la tabla pos_config)
-- ----------------------------------------------------------------------------
UPDATE ir_model_fields
   SET name = 'ickab_pos_product_label_mode'
 WHERE model = 'pos.config'
   AND name = 'product_label_mode';

UPDATE ir_model_data
   SET name = replace(name, 'product_label_mode', 'ickab_pos_product_label_mode')
 WHERE model = 'ir.model.fields'
   AND res_id IN (
        SELECT id FROM ir_model_fields
         WHERE model = 'pos.config'
           AND name = 'ickab_pos_product_label_mode'
   );

DO $$
BEGIN
  IF EXISTS (
        SELECT 1 FROM information_schema.columns
         WHERE table_name = 'pos_config'
           AND column_name = 'product_label_mode'
     ) THEN
    ALTER TABLE pos_config
      RENAME COLUMN product_label_mode TO ickab_pos_product_label_mode;
  END IF;
END
$$;

-- ----------------------------------------------------------------------------
-- 4) Marcar los módulos de origen para desinstalar
--    El siguiente arranque con ``-u sh_auto_part_vehicle`` los desinstala.
-- ----------------------------------------------------------------------------
UPDATE ir_module_module
   SET state = 'to remove'
 WHERE name IN (
        'sh_auto_part_vehicle_extends',
        'sh_product_brand_sale',
        'abt_pos_internal_reference',
        'ickab_pos_product_catalog'
 );

COMMIT;

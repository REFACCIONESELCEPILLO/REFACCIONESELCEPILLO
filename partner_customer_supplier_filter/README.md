# Clasificacion de clientes y proveedores

Este modulo controla la clasificacion operativa de los contactos en Odoo 18.

## Comportamiento

- Crea los campos `is_customer` (Es cliente) e `is_supplier` (Es proveedor).
- Al crear desde Ventas activa automaticamente la clasificacion de cliente.
- Al crear desde Compras o desde los proveedores de un producto activa
  automaticamente la clasificacion de proveedor.
- Filtra los contactos disponibles en las tres interfaces anteriores.
- Sincroniza las clasificaciones con las etiquetas `Cliente` y `Proveedor`.
- Conserva sincronizados los campos Studio `x_studio_es_cliente` y
  `x_studio_es_proveedor` cuando existen.
- Nunca reduce `customer_rank` ni `supplier_rank`.

## Migracion al instalar

La instalacion suma clasificaciones usando cualquiera de estas evidencias:

- Campo propio del modulo activo.
- Checkbox Studio activo.
- Etiqueta Cliente o Proveedor existente.
- `customer_rank > 0` o `supplier_rank > 0`.

La migracion no desactiva contactos ni elimina etiquetas anteriores. Si las
etiquetas Cliente o Proveedor no existen, el modulo las crea.

## Transicion desde Studio

Los campos Studio se mantienen como respaldo y se actualizan automaticamente.
Despues de validar la migracion en una copia de la base, pueden ocultarse de la
vista con Studio. No deben eliminarse hasta completar la validacion funcional.

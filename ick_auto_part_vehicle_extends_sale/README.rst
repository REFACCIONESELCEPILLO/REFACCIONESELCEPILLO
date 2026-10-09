ICK Auto Part Vehicle Extends Sale
==================================

Extensión independiente de Ventas para mostrador de refacciones en Odoo 18.
Conserva el formulario, las líneas, precios, impuestos, totales y chatter de
Odoo, y agrega un asistente contextual a la derecha.

Alcance de la primera versión
-----------------------------

* formulario de Venta y asistente en dos columnas;
* chatter fijo debajo de ambas columnas;
* producto activo determinado al capturar una línea o mediante la acción de
  mira en la propia línea;
* piezas compatibles, equivalencias OEM, opcionales, accesorios y alternativas;
* precio calculado con la lista de precios y fecha de la cotización;
* disponibilidad y detalle por almacén;
* diálogo OWL de compatibilidad automotriz y códigos OEM;
* agregado de recomendaciones a ``sale.order.line`` sin documento paralelo;
* diseño responsive: el asistente baja debajo de Venta en anchos menores.

Fuentes de datos
----------------

El módulo consume, sin duplicar información:

* ``sh_auto_part_vehicle``;
* ``sh_auto_part_vehicle_extends``;
* ``sh_product_brand_sale``;
* ``product_qty_warehouse``;
* relaciones comerciales estándar de ``sale`` y ``website_sale``.

Instalación
-----------

Antes de instalar, los nombres técnicos disponibles en el ``addons_path`` deben
coincidir con los módulos instalados en la base. Después se instala únicamente
``ick_auto_part_vehicle_extends_sale``.

La instalación no requiere migraciones ni crea catálogos automotrices nuevos.


Componente: sh_auto_part_vehicle
===================================

:Odoo: 18.0 (Community / Enterprise)
:Módulo: ``sh_auto_part_vehicle``
:Versión: ``18.0.10.0.0``

Resumen
-------

``sh_auto_part_vehicle`` es el componente de autopartes y vehículos de ICKAB.
Nació del módulo comercial *All In One Auto Parts Management - Advance*
(Softhealer Technologies) y, desde la versión ``18.0.10.0.0``, integra en un
único manifiesto todo el dominio: catálogo de vehículos y OEM, disponibilidad web
con búsqueda por OEM, marca de autoparte en el circuito de
venta/compra/inventario y POS, identificación del producto en el punto de venta
y catálogo/recibo del POS.

Funcionalidades integradas
--------------------------

.. list-table::
   :header-rows: 1
   :widths: 30 70

   * - Funcionalidad
     - Descripción
   * - Catálogo de vehículos, marcas, OEM, garaje y grupos
     - Base del componente: modelos ``motorcycle.*`` y ``sh.vehicle.*``,
       productos con compatibilidad por vehículo, portal de garaje y
       grupos/permisos de usuario y manager.
   * - Disponibilidad web y búsqueda por OEM
     - Campos ``ickab_default_code``, ``ickab_website_*`` y
       ``ickab_oem_codes_kanban`` en ``product.template``; búsqueda por código
       OEM en la tienda y en el buscador interno; cintillos de disponibilidad.
   * - Marca de autoparte en ventas, compras, inventario y POS
     - Campo ``ickab_brand_id`` (relacionado a la variante del producto) en
       ``sale.order.line``, ``purchase.order.line``, ``stock.move``,
       ``stock.move.line`` y ``sale.report``; marca en la tarjeta, la línea y el
       recibo del POS.
   * - Identificación del producto en el punto de venta
     - ``pos.config.ickab_pos_product_label_mode`` selecciona si el POS muestra
       la referencia interna, el nombre o ambos.
   * - Catálogo y formato de recibo del POS
     - Ajustes de tarjeta de catálogo (tamaño, imagen, tipografía) y de recibo
       (ancho de papel, texto, espaciado, logo) en ``pos.config``,
       ``res.config.settings`` y el cliente del POS.

Mapa de archivos
----------------

.. list-table::
   :header-rows: 1
   :widths: 26 30 44

   * - Área
     - Modelos / lógica
     - Vistas y assets
   * - Base de vehículos y OEM
     - ``models/motorcycle_model.py``, ``brand_model.py``, ``vehicle_eom.py``,
       ``garage_model.py``, ``product_model.py``, ``sale_order.py``,
       ``account_move.py``, ``res_config_settings.py``
     - ``views/sh_vehicle_*``, ``views/product_views.xml``,
       ``views/website_sale_templates.xml``,
       ``views/sh_vehicle_table_templates.xml``,
       ``views/sh_vehicle_dashboard.xml``; ``static/src/js/*``,
       ``static/src/scss/*``, ``static/src/components/*``
   * - Disponibilidad web y OEM
     - ``models/product_model.py`` (campos y métodos ``ickab_*``),
       ``models/vehicle_eom.py`` (``ickab_get_compatible_product``)
     - ``views/product_template_oem_views.xml``,
       ``views/website_sale_extended_templates.xml``;
       ``static/src/scss/website_sale_availability.scss``
   * - Marca de autoparte
     - ``models/sale_order.py``, ``models/purchase_order.py``,
       ``models/stock_move.py``, ``models/sale_report.py``,
       ``models/product_model.py``
     - ``views/product_brand_template_views.xml``,
       ``views/product_brand_integration_views.xml``,
       ``views/sale_report_brand_views.xml``,
       ``views/product_brand_menu_views.xml``;
       ``static/src/pos/pos_product_brand.scss``
   * - POS (identificación, catálogo y recibo)
     - ``models/pos_config.py``, ``models/res_config_settings.py``
     - ``views/res_config_settings_views.xml``;
       ``static/src/pos/pos_product_screen.js``,
       ``static/src/pos/pos_product_screen.xml``,
       ``static/src/pos/pos_product_card.xml``,
       ``static/src/pos/pos_order_line.js``,
       ``static/src/pos/pos_product_catalog.scss``,
       ``static/src/pos/pos_receipt_format.js``,
       ``static/src/pos/pos_receipt_format.xml``

Dependencias
------------

``website_sale``, ``website_sale_wishlist``, ``website_sale_comparison``,
``sale_management``, ``purchase``, ``point_of_sale``, ``product_qty_warehouse``,
``portal`` y ``stock``.

Consumidores
------------

Otros módulos propios consumen los campos publicados por este componente:

* ``elcepillo_auto_sale``: usa ``sale.order.line.ickab_brand_id`` y el panel de
  refacciones para cotizaciones.
* ``sh_auto_part_vehicle_labels``: imprime etiquetas de autoparte a partir de
  ``vehicle_oem_lines`` y de los campos de marca.

Integración de assets del punto de venta
----------------------------------------

En el POS, la marca, la identificación del producto, el catálogo y el recibo se
integran sin colisiones:

* un único ``patch(ProductScreen.prototype, …)`` en ``pos_product_screen.js``;
* un único ``patch(PosOrderline.prototype, {getDisplayData})`` en
  ``pos_order_line.js``;
* una única extensión de ``point_of_sale.ProductCard`` en
  ``pos_product_card.xml`` (marca y precio en el mismo ``xpath``);
* un único ``patch(OrderReceipt.prototype, …)`` en ``pos_receipt_format.js``.

El orden de carga se declara explícitamente en ``point_of_sale._assets_pos`` del
manifiesto.

Nota sobre ``pos.config``
-------------------------

Los campos nuevos de ``pos.config`` (ajustes de POS) se cargan automáticamente en
el cliente del POS porque ``pos.config._load_pos_data_fields`` hereda de
``pos.load.mixin``: cuando el mixin devuelve una lista vacía, Odoo expande a
todos los campos del modelo. No hace falta declararlos uno por uno.

Autoría y licencias
-------------------

El componente combina código de varios autores. El manifiesto declara ``author``
con las cuatro autorías, ``maintainer`` ICKAB y mantiene la ``license`` del código
base (``OPL-1``).

.. list-table::
   :header-rows: 1
   :widths: 40 34 26

   * - Origen
     - Autoría original
     - Licencia de origen
   * - Base (ex *All In One Auto Parts Management - Advance*)
     - Softhealer Technologies (``support@softhealer.com``)
     - OPL-1
   * - Disponibilidad web y búsqueda por OEM
     - ICKAB (basado en el patrón de Softhealer)
     - LGPL-3
   * - Marca de autoparte en ventas, compras, inventario y POS
     - Cybrosys Technologies — Adarsh K (``odoo@cybrosys.com``)
     - AGPL-3
   * - Identificación del producto en el punto de venta
     - AskByte Technolab; adaptado por ICKAB
     - LGPL-3
   * - Catálogo y formato de recibo del punto de venta
     - ICKAB
     - LGPL-3

El código portado conserva las cabeceras de copyright de origen (Cybrosys
Technologies / GNU Affero General Public License v3 en la marca de autoparte, y la
atribución *«AskByte Technolab; adapted by ICKAB»* en la identificación del
producto en POS).

Estado legal: fusión de licencias incompatible sin autorización
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

La integración produce una **obra derivada** que mezcla código ``OPL-1`` (base,
Softhealer) con código ``AGPL-3`` (marca de autoparte, Cybrosys). La licencia
``AGPL-3`` **no es compatible** con ``OPL-1`` para redistribuir el resultado bajo
una sola licencia. Por lo tanto:

#. **No publicar, vender ni distribuir** este módulo fusionado (App Store,
   repositorio público o entrega a terceros) **sin autorización explícita por
   escrito** de los titulares (Softhealer y Cybrosys), o sin sustituir la marca
   de autoparte por una implementación propia.
#. El uso interno en la instancia del cliente es aceptable dentro del marco
   contractual vigente, conservando íntegras las atribuciones de este documento y
   las cabeceras de copyright del código.
#. Cualquier alternativa (reimplementar la marca en ventas, relicenciar o
   adquirir licencia) debe documentarse aquí antes de publicar.

Hasta resolver la licencia resultante, el módulo se considera *uso interno*.

Convención de nombres
---------------------

Todo identificador técnico propio de ICKAB usa el prefijo ``ickab_``:

* campos: ``ickab_<dominio>_<nombre>`` (p. ej. ``ickab_pos_product_label_mode``,
  ``ickab_brand_id``);
* métodos: ``_compute_ickab_*``, ``_inverse_ickab_*``, ``_search_ickab_*`` o
  ``ickab_<accion>``;
* clases y variables CSS del POS: ``ickab-*`` y ``--ickab-*``;
* plantillas QWeb del POS: ``sh_auto_part_vehicle.<Nombre>``.

Los identificadores legados del código base (``motorcycle.*``, ``sh.vehicle.*``,
campos ``sh_*`` y el grupo ``group_sh_motorcycle_manager``) **se conservan**:
forman parte del esquema distribuido y renombrarlos rompería compatibilidad con
datos, i18n y terceros. Su normalización se abordará como trabajo dedicado,
siguiendo esta misma convención ``ickab_*``.

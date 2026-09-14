Auto Part Vehicle Labels 18.0.3.2.1
===================================

Motor unificado de etiquetas de autopartes para Odoo 18.

Principio de diseño 3.0
-----------------------

La geometría se resuelve una sola vez en milímetros. El preview SVG, ZPL y TSPL
consumen el mismo plan semántico: SKU/referencia interna, nombre, OEM y código
de barras cuando corresponde. Los renderers no tienen coordenadas particulares
por marca/modelo.

Las diferencias físicas pertenecen a ``ickab_direct_print``:

* perfil de compatibilidad de impresora;
* dirección y origen;
* polaridad de gráficos TSPL;
* capacidades TSPL/TSPL2;
* tipo de sensor y GAP/BLINE del consumible.

Salida
------

* Zebra/ZPL: comandos ZPL nativos.
* TSPL/TSPL2: ``TEXT`` y ``BARCODE`` nativos.
* La jerarquía tipográfica se expresa en milímetros dentro del layout. Cada
  perfil decide si puede usar fuente 0 escalable; cuando no está físicamente
  validada se usan las fuentes residentes fijas 1..5. La 4BARCODE 4B-2054L
  validada por ICKAB usa fuentes fijas por consistencia y legibilidad.

Formatos
--------

* 50 x 30 mm: SKU, nombre y hasta 7 referencias OEM; sin código de barras.
* 70 x 50 mm: SKU, nombre, hasta 8 referencias OEM y Code 128.
* 203/300 dpi; al usar Direct Print manda el DPI real de la impresora.

Integración
-----------

Depende directamente de ``ickab_direct_print``. El antiguo addon puente
``sh_auto_part_vehicle_labels_direct_print`` queda obsoleto y debe desinstalarse
una vez actualizados y validados ambos módulos principales.


Ajuste 50 x 30 mm 3.1
---------------------

La corrida física de aceptación (1, 3 y 10 etiquetas) confirmó que el avance
del rollo es estable y no existe deriva acumulativa. El layout 50 x 30 mm usa
ahora una franja superior segura de 5 mm y una jerarquía legible basada en
fuentes TSPL residentes: SKU grande, nombre medio y OEM compacto. El cambio
no altera GAP, sensor, dirección ni origen físico de la impresora.


18.0.3.2.0
------------
- 50x30: wrapping del nombre basado en pitch físico conservador de fuente TSPL residente.
- OEM: tipografía legible en etiquetas de hasta 4 referencias; modo compacto automático para 5-7.
- Sin cambios de transporte, DPI, GAP ni offsets de impresora.


18.0.3.2.1
------------
- La cabecera visible cambia de ``CODIGO`` a ``SKU``.
- Se elimina el logo de compañía de los formatos 50x30 y 70x50.
- SKU utiliza todo el ancho disponible de la cabecera, manteniendo el margen superior físico validado.
- Preview, ZPL y TSPL consumen el mismo layout sin logo.

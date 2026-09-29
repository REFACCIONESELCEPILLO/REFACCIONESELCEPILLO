Auto Part Vehicle Labels 18.0.3.5.0
===================================

Formato preestablecido de etiquetas de autopartes para Odoo 18.

Principio de diseño 3.0
-----------------------

La geometría del formato se define una sola vez en milímetros: SKU/referencia
interna, nombre, OEM y código de barras cuando corresponde. La vista previa usa
esa misma geometría. Al imprimir, el módulo entrega el formato y los datos a
``ickab_direct_print``; no selecciona lenguaje, DPI, transporte ni impresora.

Las diferencias físicas pertenecen a ``ickab_direct_print``:

* perfil de compatibilidad de impresora;
* dirección y origen;
* polaridad de gráficos TSPL;
* capacidades TSPL/TSPL2;
* tipo de sensor y GAP/BLINE del consumible.

Salida
------

La impresión física siempre pasa por ``ickab_direct_print``. Direct Print usa un
renderer nativo cuando dispone de él (por ejemplo ZPL/TSPL) o genera un PDF al
tamaño exacto y utiliza el driver del sistema operativo para otras impresoras
de etiquetas compatibles.

Formatos
--------

* 50 x 30 mm: SKU, nombre y hasta 7 referencias OEM; sin código de barras.
* 100 x 50 mm: logo de compañía, SKU, nombre multilínea, hasta 6 referencias OEM y Code 128.
* El DPI final siempre lo determina la impresora seleccionada en Direct Print.

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


18.0.3.3.0
------------
- El formato fijo se entrega a Direct Print como geometría y datos en milímetros.
- Se elimina del camino de impresión la decisión ZPL/TSPL.
- Direct Print elige renderer nativo o fallback PDF/driver según la impresora.
- El preview y las exportaciones históricas permanecen disponibles sin convertirse en un motor paralelo de impresión.


18.0.3.4.0
------------
- Sustituye el formato grande de 70x50 por el diseño solicitado de 100x50 mm.
- Agrega logo de compañía de 29x11 mm, cabecera SKU, nombre multilínea y equivalencias OEM.
- El código Code 128 ocupa un área de 51x10 mm en el bloque inferior derecho.


18.0.3.4.1
------------
- Centra horizontalmente el código de barras de 51 mm en la etiqueta.
- Aumenta a 3 mm y centra el número legible del código de barras.
- Distribuye hasta 6 equivalencias en dos columnas para evitar superposiciones.


18.0.3.5.0
------------
- Estandariza el formato 50x30 con logo, cabecera SKU, nombre multilínea y OEM en dos columnas.
- Conserva el formato compacto sin código de barras.

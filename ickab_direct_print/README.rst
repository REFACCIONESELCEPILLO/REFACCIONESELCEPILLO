ICKAB Direct Print 18.0.4.0.0
==============================

Motor de impresión directa para Odoo 18 mediante agentes locales.

Esta versión consolida el núcleo estable con compatibilidad multi-impresora y
separa explícitamente tres conceptos: transporte, lenguaje y perfil físico de
impresora. No contiene lógica de escalamiento ZPL experimental.

Cambios estructurales 4.0
-------------------------

* ``Prueba de comunicación`` valida transporte + lenguaje; ya no se presenta como
  prueba del diseño de una etiqueta de producto.
* El preámbulo físico TSPL (``SIZE``, ``GAP/BLINE``, ``DIRECTION``, ``REFERENCE``
  y ``CODEPAGE``) vive en Direct Print y es reutilizado por los generadores de
  etiquetas. La prueba técnica y la etiqueta real dejan de configurar el medio
  por caminos diferentes.
* El papel modela el sensor (GAP, BLINE o continuo), distancia y offset.
* El perfil de compatibilidad modela dirección, origen, polaridad BITMAP,
  soporte de BITMAP en línea y estrategia de fuentes TSPL definida por perfil.
* ``Descargar archivo`` genera exactamente el payload de la impresora seleccionada;
  una impresora TSPL descarga TSPL y una ZPL descarga ZPL.
* Conserva cola/API, reimpresión binaria segura y validación estricta del lenguaje.

Perfiles iniciales
------------------

* Zebra GK420d — ZPL — 203 dpi.
* 4BARCODE 4B-2054L — TSPL/TSPL2 — 203 dpi, validada físicamente por USB/Windows RAW; usa fuentes residentes fijas 1..5 por consistencia física.
* Perfiles genéricos ZPL, TSPL y EPL de 203 dpi.

Compatibilidad futura
---------------------

Una impresora nueva que utilice un lenguaje/transporte ya soportado requiere un
nuevo perfil, no un módulo nuevo. Sólo se desarrolla código cuando aparece un
lenguaje, transporte o capacidad de render no soportada.

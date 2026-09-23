ICKAB Direct Print 18.0.3.0.0
==============================

Motor único de impresión directa para Odoo 18 mediante agentes locales.

Arquitectura
------------

ICKAB Direct Print mantiene en Odoo la configuración de sucursales, usuarios,
hosts/agentes, impresoras, papeles, perfiles y cola de trabajos. Es el único
camino de impresión directa de la solución ICKAB.

Los módulos que generan contenido conservan su responsabilidad:

* Odoo estándar genera sus reportes QWeb/PDF (venta, inventario, etc.).
* ICKAB Label Studio entrega el diseño de etiqueta y sus datos.
* Auto Part Vehicle Labels entrega su formato fijo y datos de producto.
* Integraciones futuras de POS o paquetería pueden entregar su ticket/archivo ya generado.

Direct Print resuelve usuario, sucursal, impresora, papel, capacidades y salida.
El Print Agent sólo entrega el trabajo por el transporte disponible.

Etiquetas
---------

Los diseños permanecen en milímetros. Direct Print usa renderizado nativo ZPL o
TSPL cuando la impresora lo permite. Para otros lenguajes/modelos con una cola
de sistema operativo disponible, genera un PDF al tamaño físico exacto y usa el
driver de la impresora. Los payloads externos ya generados (por ejemplo ZPL de
una paquetería) se transmiten RAW únicamente cuando la impresora declara soporte.

Documentos estándar
--------------------

Los reportes PDF de Odoo no se rediseñan. Si el reporte está configurado en modo
Direct Print, el PDF original se encola y el Agent lo entrega al driver de la
impresora configurada (Carta, A4 u otro papel permitido).

Capacidades de esta versión
---------------------------

* Routing por compañía, sucursal, usuario, reporte/modelo y tipo de documento.
* Tipos de documento: etiqueta, ticket y documento.
* Cola, reimpresión, hosts/agentes y asignaciones.
* Perfiles con lenguaje preferido y lenguajes alternos.
* Renderizado nativo de etiqueta: ZPL/ZPL II y TSPL/TSPL2.
* Fallback de etiqueta por PDF/driver para impresoras con cola del sistema.
* Paso RAW de payloads ya generados: ZPL, TSPL, EPL, CPCL, ESC/POS, StarPRNT,
  SBPL, DPL, IPL/Fingerprint, Brother Raster, PCL, PostScript, PWG Raster y RAW,
  sujeto a las capacidades declaradas de la impresora/agente.
* Papeles de etiqueta, Ticket 58 mm, Ticket 80 mm, Carta y A4, además de medidas
  personalizadas.

Agente Windows 1.4.0
--------------------

El paquete Windows de esta release ejecuta Windows RAW, TCP RAW y cola/driver de
Windows. PDF/imagen se envían al driver; los lenguajes nativos se envían RAW. El
catálogo del servidor conserva otros transportes para agentes/plataformas futuras,
pero no se atribuyen al Agent Windows 1.4.0 si no están implementados allí.

18.0.3.0.0
-----------

* Direct Print pasa a ser el motor único para etiquetas diseñadas/fijas y PDF estándar.
* Elimina restricciones ZPL/TSPL de los módulos origen de etiquetas.
* Incorpora selección de lenguaje/capacidades y fallback PDF/driver para etiquetas.
* Conserva el PDF estándar de Odoo para cotizaciones, ventas e inventario.
* Expone un punto interno genérico para futuras integraciones POS/paquetería sin
  crear módulos de renderizado adicionales.

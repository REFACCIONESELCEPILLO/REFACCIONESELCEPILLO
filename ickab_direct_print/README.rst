ICKAB Direct Print 18.0.2.0.2
==============================

Motor de impresión directa para Odoo 18 mediante agentes locales.

Arquitectura
------------

ICKAB Direct Print mantiene en Odoo la configuración de impresión, sucursales,
hosts/agentes, impresoras, papeles, perfiles de compatibilidad y cola de trabajos.
El agente local consulta Odoo mediante HTTPS y entrega el payload al dispositivo;
el servidor Odoo no necesita acceso directo a la red privada del cliente.

Capacidades incluidas
---------------------

* Impresión por sucursal y compañía.
* Asignaciones de impresora por usuario, sucursal y tipo de documento.
* Hosts/agentes locales con código temporal de instalación.
* Cola de trabajos y reimpresión.
* Tipos de salida ZPL/ZPL II, TSPL/TSPL2, EPL/EPL2, ESC/POS, CPCL, PDF,
  imagen y RAW.
* Transportes Windows RAW, TCP/IP RAW, Windows Spooler, CUPS, Bluetooth,
  Android Print Service y USB OTG según capacidades del agente.
* Perfiles de compatibilidad desacoplados de la lógica del diseño.
* Configuración física de papel para GAP, BLINE y medio continuo.
* Perfiles iniciales para Zebra GK420d, 4BARCODE 4B-2054L y equipos genéricos
  ZPL/TSPL/EPL de 203 dpi.

Versión 18.0.2.0.2
------------------

* Corrige la colisión de etiquetas de los campos ``printer_ids`` y
  ``printer_count`` del modelo ``ickab.print.host``.
* ``printer_count`` usa ahora la etiqueta visible ``Número de impresoras``.
* Limpia artefactos de migración pertenecientes a versiones futuras que no
  corresponden a la serie 18.0.2.x de este paquete.
* No requiere intervención manual en consola para esta corrección.

# ICKAB Direct Print 18.0.3.0.0

## Objetivo

Direct Print queda como el único motor/camino de impresión de la solución ICKAB.
El módulo que genera el contenido conserva la responsabilidad del documento; Direct
Print resuelve usuario, sucursal, impresora, papel, copias, renderer, cola y entrega
al Print Agent.

## Cambios principales

- Los reportes PDF estándar de Odoo conservan su generación QWeb PDF y pueden enviarse
  directamente a la impresora configurada, sin rediseñarlos.
- Label Studio y Auto Part Vehicle Labels entregan el diseño/contenido de etiqueta en
  medidas físicas. Ninguno decide ZPL, TSPL, EPL ni transporte.
- Direct Print selecciona renderer nativo disponible (actualmente ZPL/TSPL) o utiliza
  PDF de tamaño físico exacto mediante el driver del sistema operativo cuando no hay
  renderer nativo para el lenguaje de la impresora.
- Una impresora puede declarar lenguaje preferido y lenguajes compatibles adicionales.
  Ejemplo: Zebra GK420d `epl` con alterno `zpl` puede utilizar el renderer ZPL sin
  modificar el diseño.
- Se amplía el catálogo de payloads para trabajos ya generados por integraciones
  externas: ZPL, TSPL, EPL, CPCL, ESC/POS, StarPRNT, SBPL, DPL, IPL, Brother Raster,
  PCL, PostScript, PWG Raster, PDF, imagen y RAW.
- Se añade un punto de entrada interno `ickab.print.engine.enqueue_payload()` para que
  futuras integraciones POS/paquetería entreguen su contenido ya generado a Direct
  Print, sin convertirlo a un formato artificial.

## Regla de arquitectura

- PDF Odoo -> Direct Print -> driver/cola -> Print Agent -> impresora.
- Diseño Label Studio -> Direct Print -> renderer/driver -> Print Agent -> impresora.
- Formato fijo Auto Part -> Direct Print -> renderer/driver -> Print Agent -> impresora.
- Payload externo ya generado -> Direct Print -> transporte compatible -> Print Agent.

## Arquitectura definitiva

- Direct Print es el único motor/camino de impresión.
- Los reportes estándar de Odoo conservan su PDF original y Direct Print lo envía a la impresora configurada.
- Los diseños de Label Studio y el formato fijo de Auto Part entregan geometría/datos; Direct Print decide la salida física.
- Para lenguajes de etiqueta sin renderer nativo, Direct Print genera un PDF al tamaño físico exacto y utiliza el driver del sistema operativo cuando existe una cola compatible.
- POS y EnviaYa podrán usar el punto interno `enqueue_payload`; sus integraciones concretas no forman parte de esta release porque no se proporcionó su código fuente.
# Impresión desde el menú Imprimir de Odoo 18

El manejador web de reportes envía los QWeb PDF y QWeb Text configurados en modo
directo o preguntar al motor de ICKAB, incluyendo cotizaciones, albaranes,
facturas y el reporte **Ticket de venta** de `module_1`. Los reportes en modo
descarga estándar conservan la descarga de Odoo.

El Ticket de venta de `module_1` es un PDF de 76 mm. En Ajustes > Técnico >
Reportes > Reportes configure ese reporte en modo directo, tipo Ticket, con
impresora y papel adecuados. Para una impresora ESC/POS que solo recibe datos
RAW por TCP se necesita un reporte ESC/POS nativo; el PDF requiere una cola con
controlador de Windows (o una impresora que acepte PDF nativamente).

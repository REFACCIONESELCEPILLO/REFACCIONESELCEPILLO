# ICKAB Label Studio 18.0.5.1.1

Corrección de robustez para imágenes en impresión directa y reportes.

## Corregido

- Los campos `Binary/Image` se leen forzando `bin_size=False`, incluso cuando el contexto del cliente web o de Direct Print trae `bin_size=True`.
- Se rechazan correctamente valores de tamaño humano como `24.6 KB` en lugar de interpretarlos como Base64.
- Se aceptan tanto valores Base64 normales de Odoo como bytes crudos de imágenes raster y `data:image/...;base64`.
- El error de imagen ahora identifica el campo/origen que falló y diferencia un formato no reconocido de SVG.
- Se mantiene compatibilidad total con los diseños Design v2 de 18.0.5.1.0.

## Motivo

En flujos iniciados desde el cliente web o un wizard de impresión, Odoo puede devolver el tamaño del binario en lugar del contenido real. La versión 18.0.5.1.0 podía decodificar accidentalmente ese texto como Base64 y Pillow terminaba mostrando `La imagen no puede ser procesada por Label Studio`.

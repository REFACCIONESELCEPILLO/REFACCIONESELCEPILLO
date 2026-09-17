# ICKAB Direct Print 18.0.2.0.2

## Objetivo

Liberación de mantenimiento para dejar el componente limpio durante la carga del
registro de Odoo 18.

## Cambios

- `ickab.print.host.printer_ids` conserva la etiqueta **Impresoras**.
- `ickab.print.host.printer_count` cambia a **Número de impresoras** para evitar
  el warning de dos campos del mismo modelo con la misma etiqueta.
- Se eliminaron del paquete 18.0.2.x scripts de actualización etiquetados como
  18.0.4.x que no corresponden a esta versión y podían generar confusión de
  mantenimiento.
- Se sincronizó la documentación principal con la versión real del manifest.

## Compatibilidad

No cambia nombres técnicos de campos, modelos, XML IDs ni contratos del agente.
El cambio de `printer_count` es únicamente de etiqueta visible.

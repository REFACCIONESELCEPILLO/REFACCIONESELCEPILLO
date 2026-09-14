# ICKAB Label Studio 18.0.5.0.0

## Cambio arquitectónico

La integración con ICKAB Direct Print ahora vive dentro de `ickab_label_studio`.
El addon `ickab_label_studio_direct_print` queda retirado y ya no es necesario.

Label Studio sigue sin declarar dependencia dura de Direct Print. Si Direct Print
no está instalado, Studio mantiene diseño, preview, importación y descarga ZPL.
Si está instalado y el usuario cuenta con permiso de impresión, Studio muestra
**Imprimir** y entrega el trabajo al flujo existente de Direct Print.

## Frontera de responsabilidades

- Label Studio: diseño WYSIWYG, datos Odoo, formato físico, preview y exportación.
- Direct Print: selección/compatibilidad de impresora, `language=auto`, cola y job.
- Print Agent: ejecución física.

Studio no valida `printer.language` ni decide ZPL/TSPL.

## Migración

Antes de validar esta versión se recomienda desinstalar
`ickab_label_studio_direct_print` para retirar la capa puente antigua. No se
deben desinstalar `ickab_label_studio` ni `ickab_direct_print`.

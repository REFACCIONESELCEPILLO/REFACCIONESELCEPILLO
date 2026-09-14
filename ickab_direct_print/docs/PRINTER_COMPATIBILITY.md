# ICKAB Direct Print — estrategia de compatibilidad

## Principio

La compatibilidad se resuelve por tres capas independientes:

1. **Tipo de salida**: etiqueta, ticket o documento.
2. **Transporte**: Windows RAW, TCP/IP RAW, Windows Spooler, CUPS, Bluetooth, Android USB OTG, etc.
3. **Lenguaje**: ZPL, TSPL/TSPL2, EPL/EPL2, ESC/POS, CPCL, PDF/Driver, Imagen/Driver o RAW.

La marca de la impresora no decide por sí sola el lenguaje. Un mismo fabricante puede tener familias con lenguajes distintos y algunos equipos implementan emulación de varios lenguajes.

## Catálogo de compatibilidad

`ickab.print.compatibility.profile` guarda una ficha por familia/modelo conocido. El catálogo puede crecer desde la interfaz sin modificar Python cuando la impresora nueva usa un lenguaje y transporte ya soportados.

Campos clave:

- fabricante y modelo;
- patrón de detección por nombre del sistema operativo;
- tipo recomendado;
- lenguaje recomendado;
- resolución;
- transporte sugerido (informativo, nunca se fuerza);
- lenguajes alternos;
- estado de validación;
- referencia técnica y notas.

La impresora conserva su transporte real. Aplicar un perfil sólo establece tipo, lenguaje y DPI.

## Alta de una nueva impresora

### Caso A — usa un lenguaje ya soportado

No requiere desarrollo. Crear un perfil, validar con `Enviar prueba`, y cambiar el estado de validación a laboratorio o producción cuando corresponda.

Ejemplos: otra Zebra ZPL 203 dpi, otra TSC/compatible TSPL 203 dpi.

### Caso B — usa un lenguaje nuevo

Se agrega el lenguaje una sola vez al núcleo de Direct Print y se implementa el renderer correspondiente en el módulo funcional que produce el documento/etiqueta. Después, todos los modelos que usen ese lenguaje se agregan como datos/perfiles, no como módulos nuevos.

### Caso C — usa un transporte nuevo

Se amplía el agente (Desktop/Android/Linux) una sola vez. El servidor Odoo sigue usando la misma cola/API.

## Validación

Estados:

- `No validado`: perfil creado pero sin evidencia suficiente.
- `Catálogo/fabricante`: especificación confirmada por documentación del fabricante.
- `Laboratorio`: prueba física ICKAB satisfactoria.
- `Producción`: validado en operación del cliente.

Nunca se debe marcar un modelo como producción sólo por similitud de nombre.

## Perfiles iniciales

- Zebra GK420d — ZPL — 203 dpi — documentación de fabricante.
- 4BARCODE 4B-2054L — TSPL — 203 dpi — prueba física ICKAB por USB/Windows RAW. Fuentes residentes fijas 1..5 validadas; font 0 escalable deshabilitada para este perfil.
- Genérico ZPL 203 dpi.
- Genérico TSPL/TSPL2 203 dpi.
- Genérico EPL/EPL2 203 dpi.

## Regla de diseño

Direct Print transporta y controla compatibilidad; no reescala ni convierte arbitrariamente un lenguaje a otro.

Los módulos que crean etiquetas deben trabajar con un layout lógico y renderizadores (por ejemplo ZPL/TSPL), seleccionados según `printer.language`. De ese modo una etiqueta mantiene el mismo contenido y dimensiones físicas sin meter lógica de marcas dentro del layout.

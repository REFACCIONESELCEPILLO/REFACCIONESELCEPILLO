# Auto Part Vehicle Labels 18.0.3.3.0

- El módulo conserva los formatos preestablecidos de autopartes.
- Ya no selecciona ni valida ZPL/TSPL por su cuenta.
- Entrega layout, productos y cantidades a ICKAB Direct Print.
- Direct Print decide cómo imprimir en la impresora configurada: renderer nativo cuando
  existe o driver universal cuando corresponde.
- Se corrige el versionado del manifest respecto de la línea funcional 18.0.3.x.

## Integración de impresión

El formato de autopartes conserva únicamente el diseño preestablecido y los datos del producto. La impresión física requiere ICKAB Direct Print; el usuario ya no selecciona DPI y el módulo no restringe la impresora a ZPL/TSPL.

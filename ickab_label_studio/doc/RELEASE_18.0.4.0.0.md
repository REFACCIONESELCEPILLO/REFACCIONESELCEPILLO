# Release 18.0.4.0.0

## Cambios principales

- Explorador relacional de campos Odoo con breadcrumbs.
- Drag & drop de rutas relacionadas completas.
- Many2one, One2many y Many2many hasta 5 niveles.
- Agregaciones explícitas para colecciones: first, last, join, count.
- Resolución de colecciones sin `mapped()` para conservar orden/cardinalidad.
- Respeto de ACL y campos visibles mediante `fields_get()` del usuario actual.
- Nuevos diseños comienzan con lienzo vacío, evitando geometría inválida en etiquetas pequeñas.
- Parser ZPL conservador: comandos con semántica no reversible obligan RAW automático.
- Importación editable rechaza ZPL que perdería comportamiento.
- Límites de importación: 2 MB, 20,000 comandos, 500 objetos de preview.
- Líneas centradas de forma consistente en canvas/preview/ZPL.
- Texto multilínea preservado en ZPL.
- Escapado ZPL migrado a `^FH_` evitando colisiones con saltos `\\&`.
- Preview de códigos inválidos no provoca una petición de barcode defectuosa.
- Bridge Direct Print 18.0.4: guardar/editar un diseño ya no sincroniza formatos de impresora; la sincronización ocurre al imprimir.

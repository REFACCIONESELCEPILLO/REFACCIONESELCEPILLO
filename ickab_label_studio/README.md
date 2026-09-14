# ICKAB Label Studio 18.0.5.0.0

Diseñador de etiquetas propietario de ICKAB para Odoo 18.

## Principio

**Studio diseña. El agente imprime.**

Label Studio no administra impresoras, drivers, USB, spoolers ni colas. Mantiene un documento de etiqueta físico y neutral; un agente/renderer opcional decide cómo materializarlo para el hardware disponible.

## Diseñador

- Geometría canónica en milímetros.
- Zoom independiente del tamaño físico.
- Grid/snap, drag & drop, resize, alineación, capas, duplicado y undo/redo.
- Texto, códigos de barras, QR, rectángulos y líneas.
- Formatos rectangulares, cuadrados, circulares y ovalados.
- Perfiles de producto, paquetería 100×150, 4×6, A6 y circulares.
- Safe zone visual.

## Explorador de campos Odoo

El modelo seleccionado expone un explorador relacional con rutas canónicas.

Ejemplos:

- `product_tmpl_id.categ_id.name`
- `partner_id.state_id.name`
- `order_line.product_id.default_code`

Se puede navegar por Many2one, One2many y Many2many hasta cinco niveles. Las relaciones múltiples requieren una operación explícita: Primero, Último, Unir o Contar. La resolución preserva el orden/cardinalidad y respeta ACL y visibilidad de campos del usuario actual.

## Importación ZPL

- Archivo `.zpl` o texto pegado.
- Conversión editable únicamente cuando la reconstrucción es segura.
- Semántica no reversible (`^FT`, `^LT`, `^LS`, `^PO`, `^PM`, `^CF`, comandos desconocidos, etc.) fuerza RAW en modo Automático.
- Nunca se descartan comandos al solicitar modo editable: si no es seguro, la importación se rechaza.
- Límite de 2 MB / 20,000 comandos y preview máximo de 500 objetos. El ZPL RAW original se conserva completo.

## WYSIWYG

Canvas, preview y ZPL comparten la misma geometría física. Las líneas se renderizan sobre el mismo eje central y los saltos de línea de texto se conservan en ZPL mediante `^FB`.

## Contrato neutral

`ickab.label.template.build_print_document()` devuelve `ickab.label.document/1`.

## Dependencias

Core:

- `base`
- `web`
- `product`

No depende de `ickab_direct_print`, hardware ni módulos verticales.

## Integración opcional con ICKAB Direct Print (18.0.5)

La integración está incorporada en este mismo addon y se detecta en runtime.
No existe dependencia dura con `ickab_direct_print` y no se requiere un addon
puente adicional. Cuando Direct Print está disponible, el botón **Imprimir**
entrega el diseño al flujo existente con lenguaje `auto`; Direct Print conserva
la responsabilidad de ZPL/TSPL y del Print Agent.

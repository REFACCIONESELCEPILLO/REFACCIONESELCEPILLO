# ICKAB Label Studio 18.0.5.3.1

Diseñador de etiquetas propietario de ICKAB para Odoo 18.

## Principio

**Studio diseña. El agente imprime.**

Label Studio no administra impresoras, drivers, USB, spoolers ni colas. Mantiene un documento de etiqueta físico y neutral; un agente/renderer opcional decide cómo materializarlo para el hardware disponible.

## Diseñador

- Geometría canónica en milímetros.
- Zoom independiente del tamaño físico.
- Grid/snap, drag & drop, resize, alineación, capas, duplicado y undo/redo.
- Texto, códigos de barras, QR, rectángulos, líneas e imágenes.
- Formatos rectangulares, cuadrados, circulares y ovalados.
- Perfiles de producto, paquetería 100×150, 4×6, A6 y circulares.
- Safe zone visual.

## Imágenes

El diseñador incorpora un objeto nativo `image` con dos orígenes principales:

- **Logo de empresa**: resuelve automáticamente el logo de `res.company`.
- **Campo imagen de Odoo**: admite campos `Image/Binary` de imagen como `image_1920` y rutas relacionadas como `product_tmpl_id.image_1920`.

Las imágenes no se almacenan dentro de `design_json`. El diseño conserva únicamente el origen, la geometría física y los parámetros térmicos. Durante preview/impresión se escala al DPI objetivo y se genera un bitmap monocromático reutilizable por los renderers. El renderer ZPL emite `^GFA`.

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

Runtime Python para imágenes:

- `Pillow` (importado en Python como `PIL`), declarado por su nombre de distribución PyPI para Odoo 18.

No depende de `ickab_direct_print`, hardware ni módulos verticales.

## Integración opcional con ICKAB Direct Print (18.0.5)

La integración está incorporada en este mismo addon y se detecta en runtime.
No existe dependencia dura con `ickab_direct_print` y no se requiere un addon
puente adicional. Cuando Direct Print está disponible, el botón **Imprimir**
entrega el diseño al flujo existente con lenguaje `auto`; Direct Print conserva
la responsabilidad de ZPL/TSPL y del Print Agent.


## 18.0.5.1.1

Corrección de lectura de imágenes Binary/Image en contextos `bin_size` y diagnóstico mejorado de formatos de imagen.


## 18.0.5.3.1

Liberación de mantenimiento. La dependencia externa de imágenes se declara como `Pillow`, que es el nombre de distribución PyPI usado por el verificador de dependencias de Odoo 18; el código Python continúa importando el paquete mediante `PIL`. Esto elimina el warning de dependencia externa sin requerir instalaciones manuales ni alterar el pipeline WebP.


## 18.0.5.3.0

Corrección arquitectónica de WebP para Odoo 18. Odoo limita deliberadamente el registro global de plugins Pillow (`Image.preinit()` + `Image._initialized = 2`), por lo que un WebP válido puede fallar con `Image.open()` dentro del worker aunque el mismo entorno lo abra fuera de Odoo. Label Studio ahora decodifica WebP de forma local mediante el backend `_webp`, sin resetear Pillow, registrar plugins globales ni alterar la política de imágenes del proceso Odoo. El resultado se normaliza a RGBA y continúa por el mismo pipeline térmico neutral.

## 18.0.5.2.0

Revisión estructural del subsistema de imágenes. La lectura, validación, rasterización y empaquetado térmico se concentran en `ickab.label.image.processor`; los campos Binary/Image se leen por ORM con `bin_size=False`; se valida que el Base64 decodificado sea realmente una imagen; se recuperan envolturas Base64 accidentales; y los errores identifican el origen sin provocar excepciones secundarias de traducción.

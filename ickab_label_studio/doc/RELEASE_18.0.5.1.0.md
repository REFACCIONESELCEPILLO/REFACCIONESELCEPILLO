# ICKAB Label Studio 18.0.5.1.0

## Imágenes nativas en el diseñador

Se incorpora el tipo de elemento `image` manteniendo el esquema maestro Design v2 y las medidas físicas en milímetros.

### Orígenes soportados

- **Logo de empresa**: obtiene automáticamente el logo de la compañía del registro; si no hay una compañía específica, usa la compañía configurada en el diseño o la compañía activa.
- **Campo imagen de Odoo**: permite arrastrar campos Image/Binary de imagen como `image_1920` y rutas relacionadas como `product_tmpl_id.image_1920`.

### Diseñador

- Nuevo botón **Logo empresa**.
- Los campos de imagen aparecen en el explorador y al arrastrarlos crean un objeto Imagen.
- Propiedades: posición/tamaño en mm, `contain`, `cover`, `stretch`, umbral blanco/negro, dithering Floyd-Steinberg e inversión.
- El logo puede visualizarse directamente en el canvas. Las imágenes dinámicas muestran un marcador en el canvas y se resuelven con el registro real en la vista previa/impresión.

### Render térmico

Las imágenes se escalan al tamaño físico y DPI objetivo, se convierten a bitmap monocromático y se incorporan al documento neutral de Label Studio. El renderer ZPL genera `^GFA`.

El documento neutral incluye `image_bitmap_b64`, `image_bytes_per_row`, `image_width_dot` e `image_height_dot`, de forma que adaptadores de otros lenguajes (por ejemplo TSPL) puedan reutilizar exactamente el mismo bitmap sin volver a interpretar la imagen original.

### Compatibilidad

Los diseños existentes 18.0.5.0.0 continúan usando Design v2 y no requieren migración de JSON.

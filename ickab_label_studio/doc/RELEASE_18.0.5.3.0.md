# ICKAB Label Studio 18.0.5.3.0

## Objetivo

Corregir de forma estructural la lectura de imágenes WebP dentro de Odoo 18 sin modificar el estado global de Pillow ni la política de seguridad/compatibilidad definida por Odoo.

## Causa raíz

Odoo 18 ejecuta `Image.preinit()` y después fija `Image._initialized = 2` en `odoo.tools.image`. Esto impide que `Image.open()` cargue posteriormente plugins no preinicializados, incluido WebP. Por eso un mismo WebP puede abrir correctamente con Python/Pillow fuera de Odoo y fallar dentro de un worker Odoo. Odoo conserva WebP como binario y lo trata de forma especial en su propio pipeline.

## Corrección

- Se detecta WebP por firma RIFF/WEBP/VP8.
- Se decodifica de forma aislada con `PIL._webp.WebPAnimDecoder`.
- No se modifica `Image._initialized`.
- No se importa ni registra `WebPImagePlugin` globalmente.
- No se altera `Image.OPEN`, `Image.ID` ni la configuración global del worker.
- Se valida dimensión antes de materializar pixeles.
- Se acepta la estructura `get_info()` de Pillow 10.x y versiones más nuevas.
- Se usa el primer frame de un WebP animado de forma determinista para la etiqueta.
- Se conserva EXIF únicamente para aplicar orientación antes de convertir a RGBA.
- Después de la decodificación, WebP entra al mismo pipeline neutral de ajuste, escala de grises, dithering, 1-bit y preview.

## No se hace

- No se actualiza Pillow.
- No se ejecutan procesos externos.
- No se convierte ni reescribe la imagen almacenada en Odoo.
- No se toca `ickab_direct_print`.

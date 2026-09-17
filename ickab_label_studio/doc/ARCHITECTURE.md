# Arquitectura — ICKAB Label Studio 18.0.5.1

## Separación de responsabilidades

```text
ICKAB Label Studio
  editor WYSIWYG, datos Odoo, geometría física, preview, import/export
        |
        |  ickab.label.document/1
        v
Print Agent / Renderer opcional
  compatibilidad de impresora, lenguaje, spooler, transporte
        |
        v
Impresora física
```

Guardar un diseño no requiere ni consulta infraestructura de impresión.

## Documento maestro

El JSON interno versión 2 almacena posiciones y tamaños físicos:

- `x_mm`
- `y_mm`
- `w_mm`
- `h_mm`

El DPI sólo interviene al renderizar.

## Datos dinámicos

Los elementos pueden guardar `field_path` con una ruta ORM relativa al modelo base.
El backend valida cada tramo mediante metadata visible para el usuario actual.

Una ruta con One2many/Many2many requiere agregación explícita (`first`, `last`, `join`, `count`).

## Imágenes

`image` es un tipo de elemento del documento maestro, no una instrucción ZPL. El origen puede ser `company_logo` o `field`. Los campos imagen se validan como rutas ORM y no se incrustan en el JSON.

En render, Label Studio resuelve la imagen, la adapta al rectángulo físico del elemento y al DPI objetivo, la convierte a monocromo y produce un bitmap neutro con `image_bitmap_b64`, `image_bytes_per_row`, `image_width_dot` e `image_height_dot`. Un renderer ZPL usa ese bitmap como `^GFA`; otros adaptadores pueden reutilizar exactamente los mismos bits.

### Compatibilidad WebP dentro de Odoo

Odoo 18 preinicializa deliberadamente un subconjunto de plugins Pillow y fija `Image._initialized = 2`. Por esa razón Label Studio no debe resetear la configuración global de Pillow ni registrar `WebPImagePlugin` para todo el worker. Los WebP se detectan por firma RIFF y se decodifican de forma aislada mediante `PIL._webp.WebPAnimDecoder`; el primer frame se convierte a RGBA y desde ahí sigue el mismo pipeline neutral que el resto de imágenes. Esta decisión mantiene aislada la compatibilidad WebP y no cambia `Image.OPEN`, `Image.ID` ni la política global de Odoo.

## Medios

`ickab.label.media` describe el material físico, nunca una impresora: forma, ancho, alto, gap/black mark/continuo, margen seguro y sangrado.

## ZPL

El renderer ZPL es una salida de referencia del core. El parser de importación es conservador: sólo declara editable un archivo que pueda reconstruirse sin perder semántica conocida. Si no, se conserva RAW.

## WYSIWYG

Canvas, HTML preview y renderer comparten la misma geometría física. Un offset de hardware pertenece al perfil/agente de impresora, no al diseño.

## Compatibilidad

Los diseños versión 1 se normalizan a versión 2 en mm. Los diseños anteriores permanecen válidos. 18.0.5.1 añade el tipo opcional `image` sin cambiar Design v2 ni requerir migración de los diseños existentes.

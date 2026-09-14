# Arquitectura — ICKAB Label Studio 18.0.4

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

## Medios

`ickab.label.media` describe el material físico, nunca una impresora: forma, ancho, alto, gap/black mark/continuo, margen seguro y sangrado.

## ZPL

El renderer ZPL es una salida de referencia del core. El parser de importación es conservador: sólo declara editable un archivo que pueda reconstruirse sin perder semántica conocida. Si no, se conserva RAW.

## WYSIWYG

Canvas, HTML preview y renderer comparten la misma geometría física. Un offset de hardware pertenece al perfil/agente de impresora, no al diseño.

## Compatibilidad

Los diseños versión 1 se normalizan a versión 2 en mm. Los diseños 18.0.3 permanecen válidos; la versión 18.0.4 añade metadata opcional para rutas relacionadas sin cambiar el schema JSON.

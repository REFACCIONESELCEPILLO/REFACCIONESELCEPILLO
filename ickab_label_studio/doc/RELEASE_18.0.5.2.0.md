# ICKAB Label Studio 18.0.5.2.0

Revisión estructural del pipeline de imágenes.

## Causa raíz corregida

La 18.0.5.1.1 sólo comprobaba que el valor recibido tuviera sintaxis Base64. Un texto puede ser Base64 válido sin ser una imagen, por lo que datos no gráficos podían llegar hasta Pillow y producir `UnidentifiedImageError`. Además, el manejador de ese error usaba `source=` como parámetro de traducción, nombre que colisiona con la firma interna de `_()` en Odoo 18 y ocultaba el diagnóstico original con `TypeError: get_text_alias() got multiple values for argument 'source'`.

## Cambios de arquitectura

- Nuevo servicio único `ickab.label.image.processor`.
- Separación explícita entre origen Odoo, decodificación, validación raster, ajuste físico, monocromatización y bitmap térmico.
- Lectura de Binary/Image mediante ORM `read()` con `bin_size=False` y sin `sudo`.
- El logo usa primero `res.company.logo`, que en Odoo 18 corresponde al `image_1920` del partner de la compañía, con fallbacks controlados.
- Validación semántica del contenido: Base64 válido ya no significa imagen válida.
- Recuperación limitada de doble Base64 generado por integraciones externas.
- Diagnósticos deterministas con ruta/origen, tamaño recibido y causa, sin incluir el contenido binario.
- Límites de tamaño/resolución para evitar imágenes excesivas.
- El bitmap final sigue siendo neutral (1 bit, negro=1) y el renderer ZPL continúa consumiéndolo con `^GFA`.

## Compatibilidad

No cambia el schema Design v2 ni los JSON existentes. Los diseños 18.0.5.x se abren sin migración.

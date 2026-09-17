# ICKAB Label Studio 18.0.5.3.1

## Objetivo

Eliminar el warning de dependencia externa de Pillow durante la carga del módulo
en Odoo 18, conservando la validación explícita de la dependencia y sin requerir
intervención manual en el contenedor.

## Cambio

- El manifest declara `Pillow` en `external_dependencies.python`.
- El código continúa usando `from PIL import ...`, que es la API de importación
  proporcionada por la distribución Pillow.
- No se modifica la estrategia WebP aislada introducida en 18.0.5.3.0.
- No se actualiza ni reemplaza la versión de Pillow del entorno Odoo.

## Motivo técnico

Odoo 18 valida primero las dependencias Python mediante metadata de distribución.
`PIL` es el namespace importable, pero la distribución instalada se llama
`Pillow`. Declarar el nombre de distribución evita el warning y mantiene una
comprobación de dependencia correcta.

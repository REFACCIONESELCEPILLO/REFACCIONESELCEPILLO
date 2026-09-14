# Campos relacionados

## Rutas

Cada elemento dinámico almacena una ruta canónica (`field_path`) relativa al modelo base.

Ejemplo:

```text
product_tmpl_id.categ_id.name
```

El diseñador navega relaciones sin crear campos `related` físicos en Odoo.

## Colecciones

Si cualquier tramo es One2many/Many2many, el elemento debe definir:

- `aggregate = first`
- `aggregate = last`
- `aggregate = join` + `separator`
- `aggregate = count`

No se selecciona un registro arbitrariamente.

## Seguridad

- Sin `sudo()` en catálogo ni resolución de datos.
- Se verifica acceso de lectura del modelo.
- `fields_get()` limita campos por grupos/visibilidad.
- Los registros recorridos se validan con `check_access('read')`.
- Relaciones a modelos no legibles no se muestran en el explorador.

## Límites

- Profundidad máxima: 5 campos.
- Máximo de valores intermedios: 500.

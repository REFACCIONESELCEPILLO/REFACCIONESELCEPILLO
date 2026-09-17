# Catálogo de campos del modelo

Desde 18.0.2.2.0 el diseñador muestra permanentemente los campos del `model_id` seleccionado.

- El cambio de modelo se observa de forma reactiva en el widget.
- Los campos pueden buscarse por etiqueta, nombre técnico o tipo.
- Al pulsar un campo normal se crea un elemento de texto con `source=field` y `field_path=<nombre técnico>`.
- Los campos `Image/Binary` reconocidos como imagen se muestran en el catálogo y crean un elemento `image` al insertarlos.
- Los campos siguen disponibles también en las propiedades de elementos Texto, Código de barras y QR. Los campos de imagen sólo pueden vincularse a elementos Imagen.
- El catálogo sólo muestra campos que el backend de Label Studio permite utilizar.

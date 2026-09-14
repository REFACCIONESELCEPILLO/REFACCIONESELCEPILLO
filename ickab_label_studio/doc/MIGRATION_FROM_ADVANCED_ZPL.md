# Migración desde advanced_zpl_label_designer_print

`ickab_label_studio` es una implementación nueva de ICKAB y no reemplaza archivos del addon anterior.

Estrategia recomendada:
1. Instalar ICKAB Label Studio en desarrollo con el addon anterior aún disponible.
2. Recrear/importar diseños en el nuevo esquema JSON.
3. Validar preview y ZPL contra etiquetas físicas.
4. Instalar `ickab_label_studio_direct_print` sólo cuando `ickab_direct_print` esté validado.
5. Desinstalar el addon anterior únicamente después de validar que no existan acciones/reportes dependientes.

No se recomienda renombrar directamente la carpeta o los modelos del addon anterior.

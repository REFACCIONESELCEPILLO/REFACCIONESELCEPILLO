# Manual de Configuración Código de barras — Odoo 18 / ICKAB

## 1. Objetivo

El addon completa y administra códigos de barras de productos sin reemplazar automáticamente los códigos que ya existan.

La regla principal es:

> **Producto con barcode:** conservar.  
> **Producto sin barcode:** generar.  
> **Nivel de categoría inexistente:** usar `00`.  
> **Categoría existente sin Código Barcode:** no generar y reportar.

---

## 2. Accesos

La configuración administrativa está en:

**Ajustes → Técnico → Configuración Código de barras**

La generación masiva también tiene acceso directo en:

**Ajustes → Técnico → Generar código de barras por lotes**

Los usuarios operativos que deban generar códigos desde productos deben tener el grupo:

**Product Barcode Generator User**

Los administradores técnicos reciben este grupo de forma implícita.

---

## 3. Crear la configuración

Sólo puede existir **una configuración activa por empresa**. Las configuraciones anteriores se archivan y se conservan como referencia histórica.

Campos principales:

| Campo | Uso |
|---|---|
| Nombre | Identifica la configuración |
| Versión | Ej. `1.0`, `2026-01` |
| Empresa | Empresa Odoo a la que aplica |
| Uso | Interno o Comercial/GS1 |
| Tipo predeterminado | Code 128, EAN-13, UPC-A, EAN-8, Code 39 o GS1-128 |
| Prefijo de empresa | Uno o varios dígitos fijos; ej. `7` |
| Niveles de categoría | 0, 1, 2 o 3 |
| Longitud | Para Code 128 / Code 39 / GS1-128 |
| Generar al crear | Opcional |
| Generar imagen | Opcional |

Para códigos internos de refacciones se recomienda iniciar con **Code 128**.

---

## 4. Código de categoría

Cada categoría involucrada en la estructura tiene el campo:

**Código Barcode**

Debe contener exactamente **2 dígitos**.

Ejemplo:

| Categoría | Código |
|---|---:|
| Suspensión | `04` |
| Amortiguadores | `07` |
| Delanteros | `03` |

### Código reservado `00`

`00` nunca se asigna a una categoría real. Significa exclusivamente que el nivel no existe.

Ejemplo, si el producto está directamente en una categoría padre:

```text
Empresa  Padre  Hija  Nieta  Consecutivo
7        07     00    00     001245
```

Código final Code 128 de 13 dígitos:

```text
7070000001245
```

Si existe todo el árbol:

```text
7 + 04 + 07 + 03 + 001245
= 7040703001245
```

---

## 5. Asignación automática de códigos de categoría

En el configurador existe el botón:

**Asignar códigos a categorías**

El botón:

1. conserva todos los códigos ya capturados;
2. busca categorías sin código;
3. asigna `01`, `02`, `03`...;
4. trabaja por grupos de categorías hermanas;
5. nunca asigna `00`.

Con dos dígitos puede haber hasta 99 códigos diferentes dentro de un mismo grupo de categorías hermanas.

---

## 6. Longitud y capacidad

La capacidad depende de cuántos dígitos se reservan para empresa y categorías.

Configuración ejemplo:

- Prefijo empresa: 1 dígito.
- Padre: 2.
- Hija: 2.
- Nieta: 2.
- Estructura fija antes del consecutivo: 7 dígitos.

### Code 128 de 13 dígitos

Quedan 6 dígitos para consecutivo:

```text
000001 ... 999999
```

Capacidad: **999,999 códigos**.

### EAN-13

EAN-13 reserva el último dígito para checksum. El payload disponible es de 12 posiciones.

Con la estructura anterior quedan 5 dígitos de consecutivo:

Capacidad: **99,999 códigos**.

### UPC-A

Con la misma estructura quedan 4 posiciones de consecutivo:

Capacidad: **9,999 códigos**.

### EAN-8

Con prefijo + 3 niveles de categoría la estructura no cabe. El configurador impedirá utilizarla hasta reducir niveles/prefijo.

### Bases de datos grandes

Si la base puede superar la capacidad calculada:

- reducir niveles de categoría incluidos en el barcode; o
- para Code 128 / Code 39 / GS1-128, aumentar la longitud configurada.

El formulario muestra siempre **Dígitos disponibles para consecutivo** y **Capacidad teórica**.

---

## 7. Validar antes de usar

Pulse:

**Validar configuración**

Se comprueba:

- prefijo numérico;
- longitud disponible;
- espacio mínimo para consecutivo;
- capacidad;
- categorías utilizadas que aún no tienen Código Barcode.

Después seleccione una **Categoría de ejemplo** y revise la pestaña **Previsualización**.

La previsualización no consume consecutivos.

---

## 8. Generar un barcode desde el producto

En el formulario de producto aparece el botón:

**Generar**

junto al campo Código de barras cuando el producto todavía no tiene barcode.

El proceso:

1. obtiene la configuración activa de la empresa;
2. obtiene la ruta de categoría;
3. sustituye niveles inexistentes por `00`;
4. valida que categorías existentes tengan código;
5. obtiene el siguiente consecutivo;
6. verifica que el barcode nunca haya sido utilizado por el generador;
7. asigna el barcode;
8. genera la imagen si está habilitada;
9. registra la operación en el historial.

Si el producto ya tiene barcode, el botón rápido no lo reemplaza.

---

## 9. Generación automática al crear producto

La opción:

**Generar automáticamente al crear producto**

hace que al guardarse una nueva variante sin barcode se ejecute la misma lógica del botón Generar.

Se recomienda activarla únicamente después de:

- completar códigos de categorías;
- validar la configuración;
- probar varios productos manualmente.

---

## 10. Generar por lotes

Abra:

**Ajustes → Técnico → Generar código de barras por lotes**

Antes de ejecutar verá:

- Productos/variantes encontrados.
- Ya tienen barcode.
- Sin barcode.

El generador procesa únicamente los registros sin barcode.

Ejemplo:

```text
Encontrados:       12,438
Con barcode:        2,317
Sin barcode:       10,121
```

Al terminar muestra:

- generados;
- productos que siguen sin barcode;
- omitidos/con error;
- detalle de los primeros 100 errores.

Un producto con categoría sin configurar se reporta y el proceso continúa con el siguiente producto.

### Imágenes en bases grandes

La opción **Generar imágenes** puede desactivarse durante una carga masiva muy grande para reducir trabajo de CPU y almacenamiento.

Después pueden generarse únicamente las imágenes faltantes mediante la acción existente **Barcode Missing Image Generator**.

---

## 11. Unicidad

El addon utiliza dos capas principales:

1. un consecutivo global controlado por Odoo/PostgreSQL;
2. un historial permanente con restricción única sobre el barcode generado.

Además se comprueba el campo `product.product.barcode` antes de asignar el valor.

El historial no permite borrado desde la interfaz administrativa y puede consultarse en:

**Ajustes → Técnico → Historial de códigos generados**

Esto evita reutilizar deliberadamente un código generado aunque posteriormente se elimine el producto original.

---

## 12. Cambiar la estructura en el futuro

No se deben recalcular los códigos históricos.

Si cambia el prefijo, longitud o estructura:

1. archive la configuración anterior;
2. cree una nueva versión;
3. valide la nueva configuración;
4. úsela únicamente para nuevos códigos.

Los productos que ya tienen barcode permanecen sin cambios.

---

## 13. EAN/UPC/GS1

Para identificadores internos, Code 128 permite una estructura flexible.

Si el barcode se utilizará comercialmente fuera de la empresa como identificador GS1/GTIN, el prefijo y la numeración deben corresponder a los identificadores oficialmente asignados a la empresa. El addon calcula/renderiza el código, pero no asigna ni registra prefijos GS1.

---

## 14. Dependencias de instalación

El addon utiliza dependencias Python y una dependencia del sistema. Deben instalarse en el servidor donde corre Odoo.

### 14.1 Dependencias Python

Use **el mismo virtualenv del servicio Odoo 18**:

```bash
VENV="/ruta/al/venv"
$VENV/bin/pip install "Pillow==10.2.0" "python-barcode==0.16.1" "treepoem==3.27.1"
```

Validación:

```bash
$VENV/bin/python - <<'PY'
import barcode
import treepoem
from PIL import Image
print('python-barcode: OK')
print('Pillow: OK')
print('treepoem: OK')
PY
```

### 14.2 Ghostscript

Ghostscript es un paquete del sistema operativo; **no se instala mediante pip**.

Ubuntu/Debian:

```bash
sudo apt update
sudo apt install -y ghostscript
gs --version
```

`treepoem` utiliza Ghostscript para el renderizado de simbologías que dependen de ese backend. El generador estructurado principal (Code 128/EAN/UPC/Code 39) utiliza `python-barcode` + `Pillow`, pero se conserva `treepoem`/Ghostscript por compatibilidad con la funcionalidad heredada ITF-14 del addon original.

### 14.3 Reinicio y actualización

Después de instalar dependencias:

```bash
sudo systemctl restart <servicio-odoo>
```

Luego actualice `barcode_generator_rl` desde Odoo o mediante `odoo-bin -u barcode_generator_rl`.


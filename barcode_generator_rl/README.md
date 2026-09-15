# Product Barcode Generator RL — Odoo 18

Addon original de Rootlevel Innovations, extendido para el proyecto ICKAB con generación estructurada, única y masiva de códigos de barras.

## Funciones principales

- Generación individual desde el botón **Generar** junto al campo `barcode` del producto.
- Generación manual desde acciones de lista/formulario, conservando los tipos disponibles del addon original.
- Generación masiva de todos los productos/variantes que **no tienen barcode**.
- Nunca reemplaza barcodes existentes durante el proceso masivo.
- Configuración por empresa desde **Ajustes → Técnico → Configuración Código de barras**.
- Prefijo numérico configurable de empresa.
- Hasta 3 niveles de categoría, 2 dígitos por nivel.
- `00` reservado para un nivel de categoría inexistente.
- Si una categoría existe pero no tiene `Código Barcode`, el producto no se genera y queda reportado.
- Consecutivo global mediante `ir.sequence`.
- Historial permanente de códigos generados para no reutilizarlos aunque un producto sea eliminado.
- Previsualización del barcode antes de uso.
- Generación opcional automática al crear/guardar un nuevo producto.
- Manual integrado en la propia pantalla de configuración.

## Estructura recomendada para Code 128 de 13 dígitos

Ejemplo con tres niveles:

```text
[Empresa 1] [Padre 2] [Hija 2] [Nieta 2] [Consecutivo 6]
7           04        07       03         001245
=> 7040703001245
```

Si sólo existe la categoría padre:

```text
7 + 07 + 00 + 00 + 001245
=> 7070000001245
```

`00` nunca debe asignarse a una categoría real.

## Capacidad

Con Code 128 de 13 dígitos, prefijo de 1 dígito y 3 niveles de categoría de 2 dígitos quedan 6 dígitos para el consecutivo: 999,999 valores. Para bases que puedan superar esa capacidad, reduzca niveles de categoría o aumente la longitud de Code 128.

El configurador calcula y muestra automáticamente la capacidad antes de ejecutar la generación.

## Flujo de configuración

1. Active modo desarrollador.
2. Abra **Ajustes → Técnico → Configuración Código de barras**.
3. Cree una configuración para la empresa.
4. Defina tipo de barcode, prefijo y niveles de categoría.
5. Capture el **Código Barcode** de 2 dígitos en las categorías o use **Asignar códigos a categorías**.
6. Seleccione una categoría de ejemplo y revise la previsualización.
7. Pulse **Validar configuración**.
8. Asigne el grupo **Product Barcode Generator User** a los usuarios que podrán generar códigos (los administradores técnicos lo reciben por defecto).
9. Use **Generar códigos faltantes** para revisar primero cuántos productos tienen/no tienen barcode y después completar los faltantes.

## Tipos

Para códigos internos se recomienda **Code 128**. EAN-13, UPC-A y EAN-8 aplican sus longitudes y dígitos de control. GS1 debe utilizarse únicamente con identificadores/prefijos válidos asignados a la empresa cuando el código vaya a usarse comercialmente fuera de la organización.

## Dependencias de instalación

Instale las dependencias Python **dentro del mismo virtualenv que utiliza el servicio Odoo**:

```bash
$VENV/bin/pip install "Pillow==10.2.0" "python-barcode==0.16.1" "treepoem==3.27.1"
```

En Ubuntu/Debian instale además Ghostscript a nivel del sistema:

```bash
sudo apt update
sudo apt install -y ghostscript
gs --version
```

- `python-barcode` + `Pillow`: generación/render de Code 128, EAN, UPC, Code 39, etc.
- `treepoem` + `Ghostscript`: se conservan para compatibilidad con el helper ITF-14 del addon original.
- Ghostscript **no** debe instalarse con `pip` ni desde código Odoo.


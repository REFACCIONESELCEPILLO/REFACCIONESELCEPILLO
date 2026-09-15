# Cambios ICKAB — 18.0.19.0.0

## Generación segura
- Se eliminó la generación aleatoria para códigos internos configurados.
- Se agregó una secuencia global de consecutivos.
- Se agregó historial permanente de códigos generados para no reutilizarlos.
- Se agregó validación contra `product.product.barcode` antes de asignar.
- Se agregó validación de duplicados en futuras altas/cambios del campo barcode.

## Configurador técnico
Ruta: **Ajustes → Técnico → Configuración Código de barras**.

Permite definir:
- empresa y versión de configuración;
- uso Interno / Comercial-GS1;
- tipo predeterminado;
- prefijo numérico de empresa;
- longitud de Code 128 / Code 39 / GS1-128;
- 0, 1, 2 o 3 niveles de categoría;
- generación automática al crear producto;
- creación de imagen;
- previsualización;
- validación y cálculo de capacidad.

## Categorías
- Campo `Código Barcode` de 2 dígitos en `product.category`.
- `00` queda reservado para un nivel que no existe.
- Una categoría real sin código provoca omisión/reporte; no se interpreta como `00`.
- Botón para asignar automáticamente códigos faltantes por grupos de categorías hermanas.

## Productos
- Botón **Generar** junto al barcode para productos sin código.
- Conservación del barcode existente por defecto.
- Auditoría de tipo, configuración, consecutivo y fecha de generación.

## Generación por lotes
Ruta directa: **Ajustes → Técnico → Generar código de barras por lotes**.

Antes de ejecutar muestra:
- total de productos/variantes;
- con barcode;
- sin barcode.

Procesa por lotes configurables y nunca sustituye barcodes ya existentes.

## Renderizado
- EAN-13, EAN-8 y UPC-A validan checksum.
- Code 128 es la opción recomendada para identificadores internos de 13 dígitos.
- GS1-128 usa el renderer específico disponible en `python-barcode`.
- Codabar fue retirado de la selección porque no estaba soportado de forma consistente por el renderer declarado en el addon original.

## Dependencias
- Pillow 10.2.0
- python-barcode 0.16.1

## 18.0.19.0.1
- Restaurada/documentada la dependencia `treepoem==3.27.1` para compatibilidad heredada.
- Documentada instalación obligatoria de Ghostscript a nivel del sistema cuando se use el backend treepoem/ITF-14.
- `external_dependencies` usa los nombres de importación correctos: `barcode`, `PIL`, `treepoem`.
- Restaurado helper legado `generate_itf14_barcode_image` sin alterar el motor principal de generación estructurada.
- Agregado `DEPENDENCIAS_UBUNTU_ODOO18.md` con comandos de instalación y validación.


## 18.0.19.0.2
- La generación masiva se ejecuta automáticamente en segundo plano mediante `ir.cron` de Odoo 18.
- Cada lote guarda los productos y su avance en la misma transacción; no requiere mantener el navegador abierto.
- Barra de progreso con actualización automática cada tres segundos en el formulario.
- El avance se publica al finalizar cada lote, con un presupuesto de cinco segundos entre productos.
- Ejecuciones persistentes, consultables en **Ajustes → Técnico → Ejecuciones de códigos de barras**.
- El alcance se limita al último ID de producto encontrado al iniciar; las nuevas altas se procesan en otra ejecución.
- Los errores de producto se reportan y el proceso continúa; los errores generales muestran un estado de atención y permiten reintentar.
- Se conservan las referencias y la tabla del asistente anterior; ahora el modelo es persistente y no se elimina por la limpieza de asistentes temporales.

### Aplicación de la actualización
Actualizar `barcode_generator_rl` con el servicio detenido durante la actualización manual, y reiniciar Odoo con el código nuevo. Recargar el navegador para cargar el widget.
La tarea **Códigos de barras: generación en segundo plano** debe estar activa y Odoo debe ejecutar sus tareas programadas. El inicio puede esperar al siguiente ciclo del programador.

### Pruebas
Se incluyen pruebas de integración Odoo en `tests/test_bulk_background.py` para cola idempotente, continuidad, avance, errores, reintento y protección de ejecuciones activas.

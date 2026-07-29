# Configurador dimensional Mocalli

**Autor y mantenedor:** Ickab

Este módulo conserva las variantes dinámicas del configurador de Odoo y conecta cada valor
comercial con el producto real que se fabrica, consume y compra.

## Configuración funcional

1. Active **Configuración dimensional Mocalli** en `Cuadro personalizado`.
2. En cada atributo indique su cálculo (`Área`, `Perímetro` o `Normal`) y active
   **Requiere componente** cuando el valor deba generar materia prima.
3. En **Valores del atributo**, capture la **Referencia interna**, el **Valor**, el **Costo** y el
   **Precio adicional**. Use el botón **Configurar** para revisar o asignar manualmente el
   producto comprable exacto. En esa pantalla también puede revisar:
   - el cálculo de consumo;
   - el factor de consumo;
   - el modo y la tarifa de venta.
4. Marque los valores `N/A` como **No genera componente**. El módulo también reconoce como
   opción vacía los valores cuyo nombre comienza con `N/A`, para conservar la compatibilidad con
   datos existentes. Estos valores no aparecen en la descripción comercial, no se envían a la
   orden de fabricación y no solicitan proveedor.
   En una configuración nueva, esos valores aparecen primero y quedan seleccionados por defecto.
   Cada combo dispone de una búsqueda avanzada por referencia interna o nombre; la ventana permite
   seleccionar una sola opción y confirmarla sin recorrer listas extensas.
   Ambos muestran el formato `Referencia interna - Nombre - Precio`. Si la referencia coincide con
   un único producto existente, se vincula automáticamente como componente.
   El precio mostrado en el configurador es el **Precio adicional unitario** del valor. El importe
   dimensional se calcula después en la línea de cotización, usando el ancho y el alto capturados.
5. En la lista de materiales, identifique cada producto `(Base)` con su
   **Atributo configurable**. El atributo debe usar creación de variantes **Instantánea** o
   **Dinámica**. Si el valor elegido todavía no existe en el producto `(Base)`, el módulo lo agrega
   y resuelve o crea su variante exacta al confirmar la venta; no es necesario volver a cargar
   manualmente todos los valores en cada producto Base.
6. Configure los proveedores en la pestaña **Compras** del producto `(Base)`. En cada tarifa
   seleccione el **Valor del atributo** que se compra a ese proveedor. Al guardar la línea, el
   módulo genera o localiza la variante exacta y restringe la tarifa a ella. Una tarifa sin valor
   funciona como proveedor general de respaldo. Por ejemplo: `Farias Process → Canva` y
   `Acriplass → Acrílico`. El producto terminado debe usar **Fabricar**; el módulo aplica
   **Reabastecer bajo pedido** y **Comprar** a la materia prima exacta.

## Flujo resultante

`Cotización configurada → orden de venta → orden de fabricación → componentes exactos →
abastecimiento/RFQ estándar de Odoo`.

La cantidad se calcula por pieza y después se multiplica por la cantidad fabricada:

- Área: `ancho_cm × alto_cm / 10 000`.
- Perímetro: `(2 × ancho_cm + 2 × alto_cm) / 100`.
- Unidad: `1`.

No forman parte de esta versión la merma, el margen, la mano de obra ni la optimización de
cortes.

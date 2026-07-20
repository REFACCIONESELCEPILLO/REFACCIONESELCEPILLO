# Configurador dimensional Mocalli

Este módulo conserva las variantes dinámicas del configurador de Odoo y conecta cada valor
comercial con el producto real que se fabrica, consume y compra.

## Configuración funcional

1. Active **Configuración dimensional Mocalli** en `Cuadro personalizado`.
2. En cada atributo indique su cálculo (`Área`, `Perímetro` o `Normal`) y active
   **Requiere componente** cuando el valor deba generar materia prima.
3. Desde **Configurar** en la línea de atributo del producto, asigne a cada valor:
   - el producto o variante comprable exacto;
   - el cálculo de consumo;
   - el factor de consumo;
   - el modo y la tarifa de venta.
4. Marque los valores `N/A` como **No genera componente**.
5. En la lista de materiales, identifique cada producto `(Base)` con su
   **Atributo configurable**. Al crear la orden de fabricación, esa línea base será sustituida
   por el producto exacto seleccionado. Los componentes fijos de la lista no se alteran.
6. Configure el producto componente con su SKU, proveedor, unidad de medida y las rutas
   estándar de Odoo necesarias. Para crear una solicitud de cotización desde la demanda de la
   orden de fabricación, use las rutas **Reabastecer bajo pedido (MTO)** y **Comprar**.

## Flujo resultante

`Cotización configurada → orden de venta → orden de fabricación → componentes exactos →
abastecimiento/RFQ estándar de Odoo`.

La cantidad se calcula por pieza y después se multiplica por la cantidad fabricada:

- Área: `ancho_cm × alto_cm / 10 000`.
- Perímetro: `(2 × ancho_cm + 2 × alto_cm) / 100`.
- Unidad: `1`.

No forman parte de esta versión la merma, el margen, la mano de obra ni la optimización de
cortes.

ICKAB Advanced Audit & Login History
====================================

Versión ICKAB
-------------
- Versión técnica del addon: 18.0.1.1.0
- Nombre técnico conservado: `mst_advanced_login_history`
- Mantenedor: ICKAB
- Sitio: https://ickab.mx
- Licencia: LGPL-3
- Traducción incluida: Español (México)

Objetivo
--------
Módulo administrativo para Odoo 18 que registra inicios y cierres de sesión,
intentos fallidos, datos de sesión, IP, navegador, sistema operativo y ubicación.
También permite auditar creación, modificación y eliminación de registros.

Cambio funcional de la edición ICKAB
-------------------------------------
La auditoría de operaciones ya NO registra indiscriminadamente todos los modelos
persistentes de Odoo. El menú **Configuration > Model Log Configuration** es el
control real de la auditoría:

1. Cree una configuración.
2. Seleccione uno o más modelos.
3. Active las operaciones a registrar: Create, Modify y/o Delete.
4. Active `Include Related Line Models` si desea incluir líneas relacionadas.

Si un modelo no está incluido en una configuración activa, sus operaciones no
se guardan en `mst.user.activity.log`.

Modelos relacionados soportados
--------------------------------
- `sale.order` -> `sale.order.line`
- `purchase.order` -> `purchase.order.line`
- `account.move` -> `account.move.line`
- `stock.picking` -> `stock.move`, `stock.move.line`

Interruptor global de emergencia
--------------------------------
Se conserva el parámetro técnico:

`mst_advanced_login_history.enable_activity_audit`

- Ausente o `1`: permite auditoría de los modelos configurados.
- `0`: desactiva completamente la auditoría create/write/unlink.

El historial de login/logout y los intentos fallidos son independientes de este
interruptor.

Seguridad
---------
Los historiales de login, intentos fallidos, Advanced Logs, Model Logs y la
configuración quedan restringidos a usuarios del grupo Administrador/Ajustes
(`base.group_system`).

Sesiones
--------
La edición ICKAB conserva sesiones simultáneas por usuario: iniciar una nueva
sesión ya no marca automáticamente como cerradas otras sesiones todavía activas.
El cierre normal de sesión actualiza solamente la sesión correspondiente.

Geolocalización
---------------
- El navegador puede aportar latitud/longitud si el usuario concede permiso.
- Requiere HTTPS (excepto localhost) para geolocalización del navegador.
- Si no hay ubicación del navegador, el módulo intenta geolocalización por IP.
- La ubicación puede abrirse en Google Maps.

Instalación / actualización
----------------------------
1. Respaldar base de datos y filestore.
2. Reemplazar la carpeta existente `mst_advanced_login_history` por esta versión.
3. Reiniciar Odoo.
4. Actualizar el módulo `mst_advanced_login_history`.
5. Crear las configuraciones de modelos que realmente se desean auditar.
6. Validar Login Logs, Failed Login Logs, Model Logs y Advanced Logs.

Importante
----------
Esta versión NO elimina los registros históricos existentes. Los registros
creados por versiones anteriores permanecen en la base de datos hasta que se
realice una depuración controlada.

Aviso legal
-----------
Edición modificada y mantenida por ICKAB. Esta edición contiene modificaciones
a software previamente distribuido bajo LGPL-3. Los derechos sobre porciones de
terceros permanecen con sus respectivos titulares. Las modificaciones,
traducciones, rediseño y funcionalidad adicional de esta edición son mantenidas
por ICKAB.

## Access control

Version 18.0.1.2.0 adds a dedicated Odoo security group:

- **Full Access to ICKAB Audit History**

Only users assigned to this group can see the ICKAB Audit History application,
open its dashboard and logs, or maintain Model Log Configuration records.

Assign the permission from:

**Settings > Users & Companies > Users > Access Rights > ICKAB Audit History**

The group is independent from Odoo's global Settings administrator group, so
access can be granted to one or several selected users without making them
Odoo administrators.

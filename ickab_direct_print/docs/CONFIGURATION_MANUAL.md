# ICKAB Direct Print — Manual de configuración para usuarios

Este manual está pensado para una persona que configura ICKAB Direct Print por primera vez. No requiere conocimientos de programación.

## 1. ¿Qué hace ICKAB Direct Print?

Permite que Odoo envíe trabajos directamente a impresoras sin descargar archivos manualmente.

Puede trabajar con:

- impresoras de etiquetas ZPL;
- impresoras de tickets ESC/POS;
- impresoras de documentos Carta/A4;
- impresoras USB;
- impresoras de red;
- agentes Windows/Linux/Android.

Funciona tanto con Odoo.sh como con Odoo on-premise.

## 2. Conceptos básicos

### Equipo / Agente

Es la PC, servidor o tablet que puede acceder físicamente a las impresoras.

Ejemplo: `PC MOSTRADOR`.

### Impresora

Es el dispositivo que imprimirá: Zebra, Epson, HP, Brother, etc.

### Papel

Define el tamaño que usará la impresora: 50x30 mm, 70x50 mm, Ticket 80 mm, Carta, A4, etc.

### Cola de impresión

Es la lista de trabajos enviados por Odoo. Permite ver si un trabajo está pendiente, imprimiéndose, terminado o con error.

---

# INSTALACIÓN INICIAL EN WINDOWS

## Paso 1. Crear el equipo en Odoo

Ve a:

**Direct Print → Configuración → Equipos / Agentes**

Pulsa **Nuevo**.

En **Nombre del equipo** escribe un nombre fácil de reconocer, por ejemplo:

- `PC MOSTRADOR`
- `CAJA 1`
- `PC ALMACÉN`

Guarda.

## Paso 2. Generar el código de instalación

Dentro del equipo pulsa:

**Generar código de instalación**

Odoo mostrará un código de 8 números válido durante 15 minutos.

Ese es el único código que necesita el instalador normal.

> No es necesario copiar UUID ni Token. Esos datos están reservados para diagnóstico o configuración avanzada.

## Paso 3. Instalar el agente en la PC

En la PC Windows:

1. Descomprime `ickab_print_agent_desktop` en una carpeta permanente, por ejemplo `C:\ICKAB\PrintAgent`.
2. Haz doble clic en `INSTALAR.bat`.
3. El asistente comprobará los requisitos.
4. Escribe la URL de Odoo.
5. Escribe el código de 8 números generado en Odoo.
6. Espera a que el asistente confirme la conexión y las impresoras detectadas.

El instalador puede ayudar a instalar Python si no está disponible.

## Paso 4. Confirmar que el equipo está en línea

Regresa a:

**Direct Print → Configuración → Equipos / Agentes**

El equipo debe mostrar el estado **En línea**.

También se llenarán automáticamente la plataforma, nombre del equipo, versión del agente y última conexión.

## Paso 5. Revisar las impresoras detectadas

Abre el equipo y pulsa **Impresoras**.

Las impresoras instaladas en Windows aparecerán automáticamente.

---

# CONFIGURAR UNA IMPRESORA

## Etiquetas Zebra USB

- Tipo: Etiquetas
- Transporte: Windows RAW
- Lenguaje: ZPL
- DPI: 203 o 300
- Papel: 50x30, 70x50 u otro permitido

## Etiquetas Zebra por red

- Tipo: Etiquetas
- Transporte: TCP/IP RAW
- Lenguaje: ZPL
- IP: dirección local de la impresora
- Puerto: normalmente 9100
- DPI: 203 o 300

La PC donde corre el agente debe poder comunicarse con esa IP.

## Tickets

- Tipo: Tickets
- Transporte: Windows RAW o TCP/IP RAW
- Lenguaje: ESC/POS
- Papel: 58 mm u 80 mm

## Documentos Carta/A4

- Tipo: Documento
- Transporte: Windows Spooler
- Lenguaje: PDF
- Papel: Carta o A4

---

# IMPRESORAS Y PAPEL PREDETERMINADOS

En **Ajustes → ICKAB Direct Print** puedes definir impresoras y papeles predeterminados para:

- Etiquetas
- Tickets
- Documentos

Esto evita que el usuario tenga que escoger la impresora en cada trabajo.

---

# CONFIGURACIÓN POR REPORTE

Los reportes de Odoo pueden configurarse con uno de estos modos:

### Descarga estándar

Odoo funciona como siempre y descarga el archivo.

### Preguntar impresora

Antes de imprimir se muestra un selector de impresora, papel y copias.

### Imprimir directamente

Odoo crea el trabajo y lo envía automáticamente a la impresora configurada.

Los reportes PDF se envían como PDF. Los reportes de texto pueden utilizar ZPL, ESC/POS o RAW.

---

# PRIMERA PRUEBA RECOMENDADA

1. Confirma que el equipo esté **En línea**.
2. Confirma que la impresora esté disponible.
3. Abre la impresora.
4. Pulsa **Enviar prueba**.
5. Ve a **Direct Print → Cola de impresión**.
6. Revisa que el trabajo termine en **Impreso**.
7. Confirma la impresión física.

---

# ODOO.SH Y ON-PREMISE

En ambos casos la instalación para el usuario es la misma.

El agente instalado en la PC inicia la comunicación con Odoo. Por eso Odoo.sh no necesita tener acceso directo a las IP privadas, USB o Bluetooth de la sucursal.

---

# SI ALGO NO FUNCIONA

## El equipo aparece Fuera de línea

- Confirma que el agente esté iniciado.
- Ejecuta `DIAGNOSTICO.bat` en la PC.
- Revisa que la PC tenga acceso a la URL de Odoo.

## No aparecen impresoras

- Confirma que la impresora esté instalada en Windows.
- Ejecuta `DIAGNOSTICO.bat`.
- Reinicia el agente.

## El código de instalación venció

Genera uno nuevo en Odoo. No necesitas crear otro equipo.

## El trabajo queda en Error

Abre el trabajo en **Cola de impresión** y revisa el mensaje de error. Comprueba transporte, lenguaje, papel e impresora.

---

# INFORMACIÓN AVANZADA

UUID, Token y capacidades JSON están disponibles para administradores, pero no forman parte del procedimiento normal de instalación.


## Dirección del servidor Odoo

El agente funciona igual en cualquiera de estos escenarios:

- **Servidor local:** `http://192.168.56.10:1902`
- **On-premise con dominio:** `https://ickab.mx`
- **Odoo.sh / nube:** `https://miempresa.odoo.com`

En Windows puedes copiar la dirección completa desde el navegador. El instalador conserva sólo el protocolo, dominio/IP y puerto, y elimina automáticamente `/web`, parámetros o fragmentos.

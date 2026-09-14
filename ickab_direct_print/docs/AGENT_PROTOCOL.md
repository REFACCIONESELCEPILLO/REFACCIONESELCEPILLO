# ICKAB Print Agent — protocolo v1

## Topología

El agente usa **sólo conexiones salientes HTTP/HTTPS** hacia Odoo. Por eso el mismo protocolo funciona con Odoo.sh y on-premise.

Cabeceras en cada petición:

```http
X-ICKAB-Host: <host.uuid>
Authorization: Bearer <host.api_token>
```

## Ciclo

1. `POST /ickab_direct_print/api/v1/heartbeat`
2. `POST /ickab_direct_print/api/v1/printers/sync`
3. `POST /ickab_direct_print/api/v1/jobs/claim`
4. `GET /ickab_direct_print/api/v1/jobs/<id>/payload`
5. `POST /ickab_direct_print/api/v1/jobs/<id>/printing`
6. El agente imprime localmente.
7. `POST .../done` o `POST .../error`.

## Heartbeat

```json
{
  "agent_version": "1.0.0",
  "platform": "Windows 11 x64",
  "platform_type": "windows",
  "hostname": "PC-MOSTRADOR-01",
  "capabilities": {
    "usb": true,
    "tcp": true,
    "bluetooth_spp": false,
    "bluetooth_ble": false,
    "android_print_service": false
  }
}
```

Android usa `platform_type=android` y puede anunciar Bluetooth.

## Transportes

* `windows_raw`: ZPL/ESC-POS/RAW sin transformación al spooler Windows.
* `tcp_raw`: bytes directos a IP:puerto, normalmente 9100.
* `windows_spooler`: PDF/imagen por driver Windows.
* `cups`: PDF/imagen por CUPS/Linux.
* `bluetooth_spp`: stream RFCOMM/SPP. Ideal para ZPL, ESC/POS y CPCL en Android.
* `bluetooth_ble`: reservado para adaptadores GATT específicos.
* `android_print_service`: PDF/documentos mediante servicio de impresión Android; requiere interacción/plugin compatible.
* `usb_otg`: reservado para dispositivos USB Android.

## Seguridad

El token identifica al host. Odoo.sh nunca necesita alcanzar una IP privada del cliente. En producción debe usarse HTTPS.

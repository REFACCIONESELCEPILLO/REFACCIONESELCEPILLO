import hmac
import json

from odoo import fields, http
from odoo.http import request


class IckabDirectPrintAgentAPI(http.Controller):

    def _response(self, payload, status=200):
        return request.make_response(
            json.dumps(payload, ensure_ascii=False, default=str),
            headers=[("Content-Type", "application/json; charset=utf-8"), ("Cache-Control", "no-store")],
            status=status,
        )

    def _body(self):
        raw = request.httprequest.data or b"{}"
        try:
            return json.loads(raw.decode("utf-8"))
        except Exception:
            return {}

    def _authenticate_host(self):
        host_uuid = request.httprequest.headers.get("X-ICKAB-Host") or ""
        auth = request.httprequest.headers.get("Authorization") or ""
        token = request.httprequest.headers.get("X-ICKAB-Token") or ""
        if auth.lower().startswith("bearer "):
            token = auth[7:].strip()
        if not host_uuid or not token:
            return None
        host = request.env["ickab.print.host"].sudo().search([("uuid", "=", host_uuid), ("active", "=", True)], limit=1)
        if not host or not hmac.compare_digest(host.api_token or "", token):
            return None
        return host

    def _printer_dict(self, printer):
        return {
            "id": printer.id,
            "name": printer.name,
            "system_uid": printer.system_uid,
            "system_name": printer.system_name,
            "device_uri": printer.device_uri,
            "source": printer.source,
            "printer_type": printer.printer_type,
            "transport": printer.transport,
            "language": printer.language,
            "dpi": printer.dpi,
            "network_host": printer.network_host,
            "network_port": printer.network_port,
            "bluetooth_address": printer.bluetooth_address,
            "bluetooth_name": printer.bluetooth_name,
            "bluetooth_spp_uuid": printer.bluetooth_spp_uuid,
            "ble_service_uuid": printer.ble_service_uuid,
            "ble_characteristic_uuid": printer.ble_characteristic_uuid,
            "usb_vendor_id": printer.usb_vendor_id,
            "usb_product_id": printer.usb_product_id,
            "default_paper": printer.default_paper_id.code if printer.default_paper_id else None,
            "papers": [paper.code for paper in printer.paper_ids],
        }

    def _host_capabilities(self, body):
        caps = body.get("capabilities") or {}
        return {
            "supports_usb": bool(caps.get("usb")),
            "supports_tcp": bool(caps.get("tcp")),
            "supports_bluetooth_spp": bool(caps.get("bluetooth_spp")),
            "supports_bluetooth_ble": bool(caps.get("bluetooth_ble")),
            "supports_android_print": bool(caps.get("android_print_service")),
            "capabilities_json": json.dumps(caps, ensure_ascii=False),
        }


    @http.route("/ickab_direct_print/api/v1/pair", type="http", auth="none", methods=["POST"], csrf=False)
    def pair_host(self, **kwargs):
        body = self._body()
        code = str(body.get("pairing_code") or "").strip()
        if not code:
            return self._response({"ok": False, "error": "pairing_code_required"}, 400)
        now = fields.Datetime.now()
        host = request.env["ickab.print.host"].sudo().search([
            ("pairing_code", "=", code),
            ("pairing_expires_at", ">=", now),
            ("active", "=", True),
        ], limit=1)
        if not host:
            return self._response({"ok": False, "error": "invalid_or_expired_pairing_code"}, 401)
        platform_type = body.get("platform_type") if body.get("platform_type") in ("windows", "linux", "android", "other") else "other"
        vals = {
            "pairing_code": False,
            "pairing_expires_at": False,
            "state": "online",
            "last_seen": now,
            "platform_type": platform_type,
            "platform": body.get("platform") or host.platform,
            "hostname": body.get("hostname") or host.hostname,
            "agent_version": body.get("agent_version") or host.agent_version,
            "ip_address": request.httprequest.remote_addr,
        }
        vals.update(self._host_capabilities(body))
        host.write(vals)
        return self._response({
            "ok": True,
            "host": {"id": host.id, "name": host.name, "uuid": host.uuid},
            "host_uuid": host.uuid,
            "token": host.api_token,
            "message": "paired",
        })

    @http.route("/ickab_direct_print/api/v1/heartbeat", type="http", auth="none", methods=["POST"], csrf=False)
    def heartbeat(self, **kwargs):
        host = self._authenticate_host()
        if not host:
            return self._response({"ok": False, "error": "unauthorized"}, 401)
        body = self._body()
        platform_type = body.get("platform_type") if body.get("platform_type") in ("windows", "linux", "android", "other") else "other"
        vals = {
            "state": "online", "last_seen": fields.Datetime.now(),
            "agent_version": body.get("agent_version") or host.agent_version,
            "platform": body.get("platform") or host.platform,
            "platform_type": platform_type,
            "hostname": body.get("hostname") or host.hostname,
            "ip_address": request.httprequest.remote_addr,
        }
        vals.update(self._host_capabilities(body))
        host.write(vals)
        return self._response({
            "ok": True,
            "server_time": fields.Datetime.now(),
            "host": {"id": host.id, "name": host.name, "uuid": host.uuid},
            "printers": [self._printer_dict(p) for p in host.printer_ids.filtered("active")],
        })

    @http.route("/ickab_direct_print/api/v1/printers/sync", type="http", auth="none", methods=["POST"], csrf=False)
    def sync_printers(self, **kwargs):
        host = self._authenticate_host()
        if not host:
            return self._response({"ok": False, "error": "unauthorized"}, 401)
        body = self._body()
        printers = body.get("printers") or []
        seen_uids = set()
        Printer = request.env["ickab.print.printer"].sudo()
        now = fields.Datetime.now()
        synced = []
        allowed_transports = dict(Printer._fields["transport"].selection)
        allowed_languages = dict(Printer._fields["language"].selection)
        for item in printers:
            system_uid = str(item.get("system_uid") or item.get("system_name") or "").strip()
            if not system_uid:
                continue
            seen_uids.add(system_uid)
            printer = Printer.search([("host_id", "=", host.id), ("system_uid", "=", system_uid)], limit=1)
            vals = {
                "name": item.get("display_name") or item.get("system_name") or system_uid,
                "company_id": host.company_id.id,
                "host_id": host.id,
                "source": "discovered",
                "system_uid": system_uid,
                "system_name": item.get("system_name") or system_uid,
                "device_uri": item.get("device_uri") or False,
                "is_system_default": bool(item.get("is_default")),
                "state": "ready" if item.get("available", True) else "unavailable",
                "last_seen": now,
                "capabilities_json": json.dumps(item.get("capabilities") or {}, ensure_ascii=False),
                "last_error": item.get("error") or False,
            }
            # Connection metadata is safe to refresh even after the administrator classifies the printer.
            for key in ("bluetooth_address", "bluetooth_name", "usb_vendor_id", "usb_product_id"):
                if item.get(key):
                    vals[key] = item.get(key)
            if not printer:
                transport = item.get("transport") if item.get("transport") in allowed_transports else "windows_spooler"
                language = item.get("language") if item.get("language") in allowed_languages else "raw"
                vals.update({
                    "printer_type": item.get("printer_type") if item.get("printer_type") in ("label", "ticket", "document") else "document",
                    "transport": transport,
                    "language": language,
                    "dpi": str(item.get("dpi")) if str(item.get("dpi")) in ("203", "300", "600") else "na",
                })
                printer = Printer.create(vals)
            else:
                printer.write(vals)
            synced.append(printer.id)
        missing = host.printer_ids.filtered(lambda p: p.source == "discovered" and p.system_uid not in seen_uids)
        if missing:
            missing.write({"state": "unavailable"})
        host.write({"state": "online", "last_seen": now})
        return self._response({"ok": True, "synced": synced, "count": len(synced)})

    @http.route("/ickab_direct_print/api/v1/jobs/claim", type="http", auth="none", methods=["POST"], csrf=False)
    def claim_jobs(self, **kwargs):
        host = self._authenticate_host()
        if not host:
            return self._response({"ok": False, "error": "unauthorized"}, 401)
        body = self._body()
        try:
            limit = max(1, min(int(body.get("limit", 3)), 10))
        except Exception:
            limit = 3
        cr = request.env.cr
        cr.execute(
            """
                SELECT j.id
                  FROM ickab_print_job j
                  JOIN ickab_print_printer p ON p.id = j.printer_id
                 WHERE j.host_id = %s AND j.state = 'queued' AND p.active = TRUE
                 ORDER BY j.id FOR UPDATE SKIP LOCKED LIMIT %s
            """, (host.id, limit),
        )
        ids = [row[0] for row in cr.fetchall()]
        jobs = request.env["ickab.print.job"].sudo().browse(ids)
        now = fields.Datetime.now()
        if jobs:
            jobs.write({"state": "claimed", "claimed_at": now})
            for job in jobs:
                job.attempts += 1
        host.write({"state": "online", "last_seen": now})
        result = []
        for job in jobs:
            result.append({
                "id": job.id, "name": job.name, "payload_type": job.payload_type,
                "mime_type": job.mime_type, "filename": job.filename, "copies": job.copies,
                "checksum": job.checksum, "payload_size": job.payload_size,
                "payload_url": f"/ickab_direct_print/api/v1/jobs/{job.id}/payload",
                "printer": self._printer_dict(job.printer_id),
                "paper": {
                    "id": job.paper_id.id, "name": job.paper_id.name, "code": job.paper_id.code,
                    "category": job.paper_id.category, "width_mm": job.paper_id.width_mm,
                    "height_mm": job.paper_id.height_mm, "orientation": job.paper_id.orientation,
                } if job.paper_id else None,
            })
        return self._response({"ok": True, "jobs": result})

    @http.route("/ickab_direct_print/api/v1/jobs/<int:job_id>/payload", type="http", auth="none", methods=["GET"], csrf=False)
    def job_payload(self, job_id, **kwargs):
        host = self._authenticate_host()
        if not host:
            return self._response({"ok": False, "error": "unauthorized"}, 401)
        job = request.env["ickab.print.job"].sudo().browse(job_id).exists()
        if not job or job.host_id != host or job.state not in ("claimed", "printing"):
            return self._response({"ok": False, "error": "job_not_available"}, 404)
        raw = job._raw_payload()
        return request.make_response(raw, headers=[
            ("Content-Type", job.mime_type or "application/octet-stream"),
            ("Content-Disposition", f'inline; filename="{job.filename or job.name}"'),
            ("X-ICKAB-Checksum", job.checksum or ""),
            ("Cache-Control", "no-store"),
        ])

    def _job_for_host(self, job_id, host, allowed_states):
        job = request.env["ickab.print.job"].sudo().browse(job_id).exists()
        if not job or job.host_id != host or job.state not in allowed_states:
            return None
        return job

    @http.route("/ickab_direct_print/api/v1/jobs/<int:job_id>/printing", type="http", auth="none", methods=["POST"], csrf=False)
    def job_printing(self, job_id, **kwargs):
        host = self._authenticate_host()
        if not host:
            return self._response({"ok": False, "error": "unauthorized"}, 401)
        job = self._job_for_host(job_id, host, ("claimed",))
        if not job:
            return self._response({"ok": False, "error": "invalid_job_state"}, 409)
        body = self._body()
        job.write({"state": "printing", "printing_at": fields.Datetime.now(), "agent_reference": body.get("agent_reference") or False})
        return self._response({"ok": True})

    @http.route("/ickab_direct_print/api/v1/jobs/<int:job_id>/done", type="http", auth="none", methods=["POST"], csrf=False)
    def job_done(self, job_id, **kwargs):
        host = self._authenticate_host()
        if not host:
            return self._response({"ok": False, "error": "unauthorized"}, 401)
        job = self._job_for_host(job_id, host, ("claimed", "printing"))
        if not job:
            return self._response({"ok": False, "error": "invalid_job_state"}, 409)
        body = self._body()
        job.write({
            "state": "done", "done_at": fields.Datetime.now(),
            "agent_reference": body.get("agent_reference") or job.agent_reference, "error_message": False,
        })
        if job.printer_id:
            job.printer_id.write({"state": "ready", "last_error": False, "last_seen": fields.Datetime.now()})
        return self._response({"ok": True})

    @http.route("/ickab_direct_print/api/v1/jobs/<int:job_id>/error", type="http", auth="none", methods=["POST"], csrf=False)
    def job_error(self, job_id, **kwargs):
        host = self._authenticate_host()
        if not host:
            return self._response({"ok": False, "error": "unauthorized"}, 401)
        job = self._job_for_host(job_id, host, ("claimed", "printing"))
        if not job:
            return self._response({"ok": False, "error": "invalid_job_state"}, 409)
        body = self._body()
        message = str(body.get("error") or "Error de impresión reportado por el agente")[:10000]
        job.write({"state": "error", "error_message": message, "agent_reference": body.get("agent_reference") or job.agent_reference})
        if job.printer_id:
            job.printer_id.write({"state": "error", "last_error": message})
        return self._response({"ok": True})

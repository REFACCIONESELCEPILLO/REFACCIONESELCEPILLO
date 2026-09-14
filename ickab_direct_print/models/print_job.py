# -*- coding: utf-8 -*-
import base64
import hashlib

from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError


TEXT_PAYLOAD_TYPES = {"zpl", "tspl", "epl", "cpcl"}


class IckabPrintJob(models.Model):
    _name = "ickab.print.job"
    _description = "ICKAB Print Job"
    _order = "id desc"

    name = fields.Char(default=lambda self: _("Nuevo"), readonly=True, copy=False, index=True)
    company_id = fields.Many2one("res.company", required=True, default=lambda self: self.env.company, index=True)
    user_id = fields.Many2one("res.users", required=True, default=lambda self: self.env.user, index=True)
    printer_id = fields.Many2one(
        "ickab.print.printer", required=True, ondelete="restrict",
        domain="[('company_id', '=', company_id), ('active', '=', True)]", index=True,
    )
    host_id = fields.Many2one(related="printer_id.host_id", store=True, index=True)
    paper_id = fields.Many2one("ickab.print.paper", ondelete="restrict")
    report_id = fields.Many2one("ir.actions.report", ondelete="set null")
    source_model = fields.Char(index=True)
    source_res_id = fields.Integer(index=True)
    source_display_name = fields.Char()
    payload_type = fields.Selection(
        [
            ("zpl", "ZPL"), ("tspl", "TSPL / TSPL2"), ("epl", "EPL / EPL2"),
            ("escpos", "ESC/POS"), ("cpcl", "CPCL"), ("pdf", "PDF"),
            ("image", "Imagen"), ("raw", "RAW"),
        ],
        required=True, index=True,
    )
    payload_text = fields.Text(groups="ickab_direct_print.group_direct_print_manager")
    payload_data = fields.Binary(attachment=True, groups="ickab_direct_print.group_direct_print_manager")
    filename = fields.Char()
    mime_type = fields.Char()
    checksum = fields.Char(readonly=True, index=True)
    payload_size = fields.Integer(readonly=True)
    copies = fields.Integer(default=1, required=True)
    state = fields.Selection(
        [("queued", "Pendiente"), ("claimed", "Asignado"), ("printing", "Imprimiendo"),
         ("done", "Impreso"), ("error", "Error"), ("cancelled", "Cancelado")],
        default="queued", required=True, readonly=True, copy=False, index=True,
    )
    queued_at = fields.Datetime(default=fields.Datetime.now, readonly=True)
    claimed_at = fields.Datetime(readonly=True)
    printing_at = fields.Datetime(readonly=True)
    done_at = fields.Datetime(readonly=True)
    attempts = fields.Integer(default=0, readonly=True)
    agent_reference = fields.Char(readonly=True)
    error_message = fields.Text(readonly=True)

    @api.model_create_multi
    def create(self, vals_list):
        seq = self.env["ir.sequence"]
        for vals in vals_list:
            if vals.get("name", _("Nuevo")) == _("Nuevo"):
                vals["name"] = seq.next_by_code("ickab.print.job") or _("Nuevo")
            if vals.get("payload_text") and not vals.get("checksum"):
                raw = vals["payload_text"].encode("utf-8")
                vals["checksum"] = hashlib.sha256(raw).hexdigest()
                vals["payload_size"] = len(raw)
            elif vals.get("payload_data") and not vals.get("checksum"):
                data = vals["payload_data"]
                if isinstance(data, str):
                    data = data.encode("ascii")
                try:
                    raw = base64.b64decode(data)
                except Exception:
                    raw = b""
                vals["checksum"] = hashlib.sha256(raw).hexdigest()
                vals["payload_size"] = len(raw)
        return super().create(vals_list)

    @api.constrains("copies")
    def _check_copies(self):
        for job in self:
            if job.copies < 1:
                raise ValidationError(_("El número de copias debe ser al menos 1."))

    @api.constrains("paper_id", "printer_id")
    def _check_paper_printer(self):
        for job in self:
            if job.paper_id and job.printer_id.paper_ids and job.paper_id not in job.printer_id.paper_ids:
                raise ValidationError(_("El papel seleccionado no está permitido para la impresora."))

    @api.model
    def enqueue(self, *, printer, payload_type, payload, paper=None, copies=1,
                source_record=None, report=None, filename=None, mime_type=None):
        if not printer:
            raise UserError(_("Debe indicar una impresora."))
        native_languages = {"zpl", "tspl", "epl", "escpos", "cpcl"}
        if (
            printer.language in native_languages
            and payload_type in native_languages
            and payload_type != printer.language
        ):
            raise UserError(_(
                "La impresora %(printer)s está configurada como %(language)s y el trabajo fue generado como %(payload)s. "
                "Direct Print no convierte lenguajes de impresora: el módulo que genera el documento debe renderizarlo en el lenguaje seleccionado."
            ) % {
                "printer": printer.display_name,
                "language": (printer.language or "RAW").upper(),
                "payload": (payload_type or "RAW").upper(),
            })
        vals = {
            "company_id": printer.company_id.id,
            "user_id": self.env.user.id,
            "printer_id": printer.id,
            "paper_id": paper.id if paper else False,
            "report_id": report.id if report else False,
            "payload_type": payload_type,
            "copies": copies,
            "filename": filename,
            "mime_type": mime_type or self._default_mime_type(payload_type),
        }
        if source_record:
            source_record.ensure_one()
            vals.update({
                "source_model": source_record._name,
                "source_res_id": source_record.id,
                "source_display_name": source_record.display_name,
            })
        if isinstance(payload, str) and payload_type in TEXT_PAYLOAD_TYPES:
            vals["payload_text"] = payload
        else:
            if isinstance(payload, str):
                payload = payload.encode("utf-8")
            vals["payload_data"] = base64.b64encode(payload or b"")
        return self.create(vals)

    @api.model
    def _default_mime_type(self, payload_type):
        return {
            "zpl": "text/plain", "tspl": "text/plain", "epl": "text/plain", "cpcl": "text/plain",
            "escpos": "application/octet-stream", "pdf": "application/pdf", "image": "image/png",
            "raw": "application/octet-stream",
        }.get(payload_type, "application/octet-stream")

    def _raw_payload(self):
        self.ensure_one()
        # Compatibilidad hacia atrás: los trabajos CPCL/RAW antiguos pueden estar
        # almacenados en payload_data aunque hoy los lenguajes de texto usen payload_text.
        if self.payload_type in TEXT_PAYLOAD_TYPES and self.payload_text:
            return self.payload_text.encode("utf-8")
        data = self.payload_data or b""
        if isinstance(data, str):
            data = data.encode("ascii")
        return base64.b64decode(data) if data else b""

    def action_open_job(self):
        self.ensure_one()
        return {"type": "ir.actions.act_window", "name": self.name, "res_model": "ickab.print.job", "res_id": self.id, "view_mode": "form"}

    def action_refresh_status(self):
        self.ensure_one()
        return {"type": "ir.actions.client", "tag": "reload"}

    def action_retry(self):
        for job in self:
            if job.state not in ("error", "cancelled"):
                raise UserError(_("Sólo se pueden reintentar trabajos con error o cancelados."))
            job.write({
                "state": "queued", "queued_at": fields.Datetime.now(), "claimed_at": False,
                "printing_at": False, "done_at": False, "error_message": False, "agent_reference": False,
            })
        return True

    def action_reprint(self):
        self.ensure_one()
        raw = self.sudo()._raw_payload()
        # Los lenguajes de etiqueta pueden viajar como texto o como binario
        # (por ejemplo TSPL BITMAP). Sólo se decodifica cuando el trabajo
        # original realmente se almacenó como payload_text.
        if self.payload_type in TEXT_PAYLOAD_TYPES and self.payload_text:
            payload = raw.decode("utf-8", errors="replace")
        else:
            payload = raw
        new_job = self.enqueue(
            printer=self.printer_id, payload_type=self.payload_type, payload=payload,
            paper=self.paper_id, copies=self.copies, report=self.report_id,
            filename=self.filename, mime_type=self.mime_type,
        )
        return new_job.action_open_job()

    def action_cancel(self):
        for job in self:
            if job.state not in ("queued", "claimed"):
                raise UserError(_("Sólo se pueden cancelar trabajos pendientes o asignados."))
            job.state = "cancelled"
        return True

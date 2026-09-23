# -*- coding: utf-8 -*-
import base64
import hashlib

from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError


TEXT_PAYLOAD_TYPES = {"zpl", "tspl", "epl", "cpcl", "sbpl", "dpl", "ipl", "fingerprint"}


class IckabPrintJob(models.Model):
    _name = "ickab.print.job"
    _description = "ICKAB Print Job"
    _order = "id desc"

    name = fields.Char(default=lambda self: _("Nuevo"), readonly=True, copy=False, index=True)
    company_id = fields.Many2one("res.company", required=True, default=lambda self: self.env.company, index=True)
    user_id = fields.Many2one("res.users", required=True, default=lambda self: self.env.user, index=True)
    branch_id = fields.Many2one(
        "ickab.print.branch", string="Sucursal",
        compute="_compute_branch_id", search="_search_branch_id", readonly=True,
    )
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
            ("zpl", "ZPL / ZPL II"), ("tspl", "TSPL / TSPL2"), ("epl", "EPL / EPL2"),
            ("cpcl", "CPCL"), ("escpos", "ESC/POS"), ("starprnt", "StarPRNT"),
            ("sbpl", "SATO SBPL"), ("dpl", "Datamax DPL"), ("ipl", "Intermec IPL"),
            ("fingerprint", "Intermec Fingerprint / Direct Protocol"),
            ("brother_raster", "Brother Raster / P-touch"),
            ("pcl", "PCL"), ("postscript", "PostScript"), ("pwg_raster", "PWG Raster"),
            ("pdf", "PDF"), ("image", "Imagen"), ("raw", "RAW"),
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

    def _compute_branch_id(self):
        Context = self.env["ickab.print.job.context"]
        contexts = Context.search([("job_id", "in", self.ids)]) if self.ids else Context
        by_job = {context.job_id.id: context.branch_id for context in contexts}
        for job in self:
            job.branch_id = by_job.get(job.id) or job.printer_id.branch_id

    @api.model
    def _search_branch_id(self, operator, value):
        # branch_id is intentionally non-stored so a code deployment cannot break
        # the historical ickab_print_job table before the module is upgraded.
        # Searches combine the explicit job context with the printer/host branch,
        # which also keeps legacy jobs (created before multisucursal) searchable.
        if operator not in ("=", "!=", "in", "not in"):
            return [("id", "=", 0)]

        Context = self.env["ickab.print.job.context"]
        positive_operator = "=" if operator in ("=", "!=") else "in"
        positive_value = value

        contexts = Context.search([("branch_id", positive_operator, positive_value)])
        context_job_ids = contexts.mapped("job_id").ids
        printers = self.env["ickab.print.printer"].search([
            ("branch_id", positive_operator, positive_value),
        ])
        printer_job_ids = self.search([("printer_id", "in", printers.ids)]).ids if printers else []
        matched_ids = list(set(context_job_ids + printer_job_ids))

        if operator in ("=", "in"):
            # '=' False means jobs with no explicit context and a printer without branch.
            if operator == "=" and value is False:
                contextualized = Context.search([]).mapped("job_id").ids
                branched_printers = self.env["ickab.print.printer"].search([("branch_id", "!=", False)])
                return [
                    ("id", "not in", list(set(contextualized + self.search([
                        ("printer_id", "in", branched_printers.ids)
                    ]).ids))),
                ]
            return [("id", "in", matched_ids)]
        return [("id", "not in", matched_ids)]

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
                source_record=None, report=None, filename=None, mime_type=None, branch=None):
        if not printer:
            raise UserError(_("Debe indicar una impresora."))
        accepted = printer.accepted_payload_types()
        if payload_type not in accepted:
            raise UserError(_(
                "La impresora %(printer)s no puede recibir directamente el payload %(payload)s. "
                "Direct Print declara como compatibles: %(accepted)s."
            ) % {
                "printer": printer.display_name,
                "payload": (payload_type or "RAW").upper(),
                "accepted": ", ".join(sorted(code.upper() for code in accepted)),
            })
        branch = branch or printer.branch_id
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
        job = self.create(vals)
        if branch:
            self.env["ickab.print.job.context"].create({
                "job_id": job.id,
                "branch_id": branch.id,
            })
        return job

    @api.model
    def _default_mime_type(self, payload_type):
        return {
            "zpl": "application/octet-stream", "tspl": "application/octet-stream",
            "epl": "application/octet-stream", "cpcl": "application/octet-stream",
            "escpos": "application/octet-stream", "starprnt": "application/octet-stream",
            "sbpl": "application/octet-stream", "dpl": "application/octet-stream",
            "ipl": "application/octet-stream", "fingerprint": "application/octet-stream",
            "brother_raster": "application/octet-stream", "pcl": "application/octet-stream",
            "postscript": "application/postscript", "pwg_raster": "image/pwg-raster",
            "pdf": "application/pdf", "image": "image/png", "raw": "application/octet-stream",
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
            filename=self.filename, mime_type=self.mime_type, branch=self.branch_id,
        )
        return new_job.action_open_job()

    def action_cancel(self):
        for job in self:
            if job.state not in ("queued", "claimed"):
                raise UserError(_("Sólo se pueden cancelar trabajos pendientes o asignados."))
            job.state = "cancelled"
        return True

# -*- coding: utf-8 -*-
import base64
import json

from odoo import api, fields, models, _
from odoo.exceptions import UserError


class IckabDirectPrintWizard(models.TransientModel):
    _name = "ickab.direct.print.wizard"
    _description = "ICKAB Direct Print Wizard"

    report_id = fields.Many2one("ir.actions.report", string="Reporte a imprimir", required=True, readonly=True)
    res_model = fields.Char(readonly=True)
    res_ids_json = fields.Text(default="[]", readonly=True)
    report_data_json = fields.Text(default="{}", readonly=True)
    document_kind = fields.Selection(
        [("label", "Etiqueta"), ("ticket", "Ticket"), ("document", "Documento")],
        string="Tipo de impresión",
        required=True,
        default="document",
    )
    available_printer_ids = fields.Many2many(
        "ickab.print.printer",
        compute="_compute_available_printer_ids",
        string="Impresoras compatibles",
    )
    printer_id = fields.Many2one(
        "ickab.print.printer",
        string="Impresora",
        required=True,
        domain="[('id', 'in', available_printer_ids)]",
    )
    paper_id = fields.Many2one(
        "ickab.print.paper",
        string="Formato / papel seleccionado",
        domain="['|', ('company_id', '=', False), ('company_id', '=', company_id), ('category', '=', document_kind)]",
    )
    paper_locked = fields.Boolean(
        string="Formato definido por el documento",
        readonly=True,
        default=False,
    )
    copies = fields.Integer(string="Número de copias", default=1, required=True)
    company_id = fields.Many2one("res.company", required=True, default=lambda self: self.env.company, readonly=True)
    download_payload = fields.Binary(string="Archivo renderizado", readonly=True, attachment=False)
    download_filename = fields.Char(string="Nombre de archivo", readonly=True)
    printer_state = fields.Selection(related="printer_id.state", string="Estado de la impresora", readonly=True)
    host_state = fields.Selection(related="printer_id.host_id.state", string="Estado del equipo", readonly=True)

    @api.depends("company_id", "document_kind", "paper_id")
    def _compute_available_printer_ids(self):
        Printer = self.env["ickab.print.printer"]
        for wizard in self:
            domain = [
                ("company_id", "=", wizard.company_id.id or self.env.company.id),
                ("printer_type", "=", wizard.document_kind),
                ("active", "=", True),
            ]
            printers = Printer.search(domain)
            if wizard.paper_id:
                printers = printers.filtered(
                    lambda printer: not printer.paper_ids or wizard.paper_id in printer.paper_ids
                )
            wizard.available_printer_ids = printers

    @api.onchange("paper_id", "document_kind", "company_id")
    def _onchange_paper_compatibility(self):
        for wizard in self:
            if wizard.printer_id and wizard.printer_id not in wizard.available_printer_ids:
                wizard.printer_id = False

    @api.onchange("printer_id")
    def _onchange_printer_id(self):
        for wizard in self:
            if not wizard.printer_id:
                continue
            # Si el reporte ya definió el tamaño físico (por ejemplo 50x30 o 70x50),
            # la impresora NO debe sustituirlo por su papel predeterminado.
            if wizard.paper_locked and wizard.paper_id:
                if wizard.printer_id.paper_ids and wizard.paper_id not in wizard.printer_id.paper_ids:
                    wizard.printer_id = False
                continue
            if wizard.printer_id.default_paper_id:
                wizard.paper_id = wizard.printer_id.default_paper_id
            elif wizard.printer_id.paper_ids and len(wizard.printer_id.paper_ids) == 1:
                wizard.paper_id = wizard.printer_id.paper_ids[0]

    def _decoded_payload(self):
        self.ensure_one()
        try:
            res_ids = json.loads(self.res_ids_json or "[]")
            data = json.loads(self.report_data_json or "{}")
        except (TypeError, ValueError) as exc:
            raise UserError(_("No se pudo recuperar la información del reporte: %s") % exc) from exc
        return res_ids, data

    def action_print(self):
        self.ensure_one()
        if self.copies < 1:
            raise UserError(_("El número de copias debe ser al menos 1."))
        if self.printer_id.paper_ids and self.paper_id and self.paper_id not in self.printer_id.paper_ids:
            raise UserError(_("El papel seleccionado no está permitido para esta impresora."))
        res_ids, data = self._decoded_payload()
        return self.report_id._ickab_enqueue_direct_print(
            res_ids=res_ids,
            data=data,
            printer=self.printer_id,
            paper=self.paper_id,
            copies=self.copies,
        )

    def action_download(self):
        """Download exactly the payload that the selected printer would receive.

        The old path fell back to the report's standard QWeb download, which can
        be ZPL even after the user selected a TSPL printer. That made diagnostics
        misleading and broke the one-renderer-per-printer contract.
        """
        self.ensure_one()
        if not self.printer_id:
            raise UserError(_("Seleccione una impresora para renderizar el archivo."))
        res_ids, data = self._decoded_payload()
        payload_type, payload = self.report_id._ickab_render_payload(
            res_ids=res_ids, data=data, printer=self.printer_id
        )
        raw = payload.encode("utf-8") if isinstance(payload, str) else bytes(payload or b"")
        filename = self.report_id._ickab_filename(payload_type)
        self.write({
            "download_payload": base64.b64encode(raw),
            "download_filename": filename,
        })
        return {
            "type": "ir.actions.act_url",
            "url": "/web/content/ickab.direct.print.wizard/%s/download_payload/%s?download=true" % (self.id, filename),
            "target": "self",
        }

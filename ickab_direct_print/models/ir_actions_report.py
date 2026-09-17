# -*- coding: utf-8 -*-
import json

from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError


class IrActionsReport(models.Model):
    _inherit = "ir.actions.report"

    ickab_print_mode = fields.Selection(
        [
            ("standard", "Descarga estándar de Odoo"),
            ("ask", "Preguntar impresora antes de imprimir"),
            ("direct", "Imprimir directamente"),
        ],
        string="Modo ICKAB Direct Print",
        default="standard",
        required=True,
    )
    ickab_document_kind = fields.Selection(
        [("label", "Etiqueta"), ("ticket", "Ticket"), ("document", "Documento")],
        string="Tipo de documento",
        default="document",
        required=True,
    )
    ickab_printer_id = fields.Many2one(
        "ickab.print.printer",
        string="Impresora predeterminada",
        domain="[('company_id', '=', company_id), ('printer_type', '=', ickab_document_kind), ('active', '=', True)]",
    )
    # company_id is not a native report field. This computed helper is only used by domains.
    company_id = fields.Many2one("res.company", compute="_compute_ickab_company", string="Compañía")
    ickab_paper_id = fields.Many2one(
        "ickab.print.paper",
        string="Papel predeterminado",
        domain="['|', ('company_id', '=', False), ('company_id', '=', company_id), ('category', '=', ickab_document_kind)]",
    )
    ickab_copies = fields.Integer(string="Copias", default=1)
    ickab_text_language = fields.Selection(
        [
            ("auto", "Automático según impresora"),
            ("zpl", "ZPL / ZPL II"),
            ("tspl", "TSPL / TSPL2"),
            ("epl", "EPL / EPL2"),
            ("escpos", "ESC/POS"),
            ("cpcl", "CPCL"),
            ("raw", "RAW genérico"),
        ],
        string="Lenguaje para reportes de texto",
        default="auto",
        required=True,
    )
    ickab_fallback_download = fields.Boolean(
        string="Descargar si no hay impresora",
        default=True,
        help="Si no es posible resolver una impresora, conserva el comportamiento estándar de Odoo.",
    )

    @api.depends_context("company")
    def _compute_ickab_company(self):
        for report in self:
            report.company_id = self.env.company

    @api.constrains("ickab_copies")
    def _check_ickab_copies(self):
        for report in self:
            if report.ickab_copies < 1:
                raise ValidationError(_("El número de copias debe ser al menos 1."))

    def _ickab_normalize_res_ids(self, docids):
        if not docids:
            return []
        if isinstance(docids, models.Model):
            return docids.ids
        if isinstance(docids, int):
            return [docids]
        return [int(value) for value in docids]

    def _ickab_default_printer_paper(self, *, user=None, company=None, branch=None):
        self.ensure_one()
        user = user or self.env.user
        company = company or self.env.company
        branch = branch or user._ickab_resolve_print_branch(company)

        # 1) Perfil avanzado: permite reglas específicas por reporte/modelo/usuario/sucursal.
        profile = self.env["ickab.print.profile"].resolve_profile(
            self.ickab_document_kind,
            report=self,
            user=user,
            company=company,
            model_name=self.model,
            branch=branch,
        )
        if profile:
            return profile.printer_id, profile.paper_id, profile.copies, branch

        # 2) Asignación operativa usuario + sucursal + tipo de impresión.
        assignment = self.env["ickab.print.assignment"].resolve_assignment(
            self.ickab_document_kind, user=user, company=company, branch=branch
        )
        if assignment:
            paper = assignment.paper_id or assignment.printer_id.default_paper_id
            return assignment.printer_id, paper, assignment.copies, branch

        # 3) Impresora fijada directamente en el reporte, si pertenece a la sucursal actual
        # o si aún es una impresora legacy sin sucursal.
        printer = self.env["ickab.print.printer"]
        if self.ickab_printer_id and (
            not branch or not self.ickab_printer_id.branch_id or self.ickab_printer_id.branch_id == branch
        ):
            printer = self.ickab_printer_id

        # 4) Predeterminada de la sucursal.
        if not printer and branch:
            printer = branch.default_printer_for(self.ickab_document_kind)

        # 5) Fallback legacy/global de compañía.
        if not printer:
            if self.ickab_document_kind == "label":
                company_printer = company.ickab_default_label_printer_id
            elif self.ickab_document_kind == "ticket":
                company_printer = company.ickab_default_ticket_printer_id
            else:
                company_printer = company.ickab_default_document_printer_id
            # Un fallback legacy sin sucursal sigue siendo válido. Una impresora ya
            # asociada a otra sucursal nunca debe cruzarse accidentalmente.
            if company_printer and (
                not company_printer.branch_id or not branch or company_printer.branch_id == branch
            ):
                printer = company_printer

        if self.ickab_paper_id:
            paper = self.ickab_paper_id
        elif printer and printer.default_paper_id:
            paper = printer.default_paper_id
        elif branch and branch.default_paper_for(self.ickab_document_kind):
            paper = branch.default_paper_for(self.ickab_document_kind)
        elif self.ickab_document_kind == "label":
            paper = company.ickab_default_label_paper_id
        elif self.ickab_document_kind == "ticket":
            paper = company.ickab_default_ticket_paper_id
        else:
            paper = company.ickab_default_document_paper_id
        return printer, paper, self.ickab_copies or 1, branch


    def _ickab_requested_paper(self, data=None):
        """Return a paper explicitly requested by the originating report/wizard.

        Report generators may place ``ickab_paper_code`` in their report data.
        This is intentionally generic: Direct Print does not need a dependency
        on the module that created the report.
        """
        self.ensure_one()
        data = data or {}
        code = data.get("ickab_paper_code")
        if not code:
            return self.env["ickab.print.paper"]
        return self.env["ickab.print.paper"].search([
            ("code", "=", code),
            "|", ("company_id", "=", False), ("company_id", "=", self.env.company.id),
        ], limit=1)

    def _ickab_printer_supports_paper(self, printer, paper):
        self.ensure_one()
        return bool(printer and (not paper or not printer.paper_ids or paper in printer.paper_ids))

    def _ickab_payload_type(self, printer):
        self.ensure_one()
        if self.report_type == "qweb-pdf":
            return "pdf"
        if self.report_type != "qweb-text":
            raise UserError(_("ICKAB Direct Print soporta de forma genérica reportes QWeb PDF y QWeb Text."))
        if self.ickab_text_language != "auto":
            return self.ickab_text_language
        if printer and printer.language in ("zpl", "tspl", "epl", "escpos", "cpcl", "raw"):
            return printer.language
        return "raw"

    def _ickab_render_payload(self, res_ids=None, data=None, printer=None):
        self.ensure_one()
        res_ids = res_ids or []
        payload_type = self._ickab_payload_type(printer)
        render_data = dict(data or {})
        # Contrato genérico para módulos generadores: la impresora seleccionada
        # informa lenguaje y DPI reales sin que Direct Print conozca el diseño.
        if printer:
            render_data["ickab_target_language"] = printer.language or "raw"
            if printer.dpi in ("203", "300", "600"):
                render_data["ickab_target_dpi"] = int(printer.dpi)
            render_data["ickab_target_printer_id"] = printer.id
        content, rendered_type = self._render(self.report_name, res_ids, data=render_data)
        if self.report_type == "qweb-pdf" and rendered_type != "pdf":
            raise UserError(_("Odoo no devolvió un PDF para el reporte %s.") % self.display_name)
        if isinstance(content, str):
            raw = content.encode("utf-8")
        else:
            raw = bytes(content or b"")
        if payload_type in ("zpl", "tspl", "epl", "cpcl"):
            return payload_type, raw.decode("utf-8", errors="replace")
        return payload_type, raw

    def _ickab_filename(self, payload_type):
        self.ensure_one()
        ext = {"pdf": "pdf", "zpl": "zpl", "tspl": "tspl", "epl": "epl", "escpos": "bin", "cpcl": "cpcl", "raw": "bin", "image": "png"}.get(payload_type, "bin")
        safe = "".join(ch if ch.isalnum() or ch in "-_." else "_" for ch in (self.name or "report"))
        return f"{safe}.{ext}"

    def _ickab_enqueue_direct_print(self, *, res_ids=None, data=None, printer=None, paper=None, copies=None, branch=None):
        self.ensure_one()
        company = self.env.company
        if not company.ickab_direct_print_enabled:
            raise UserError(_("ICKAB Direct Print no está habilitado para la compañía actual."))
        default_printer, default_paper, default_copies, resolved_branch = self._ickab_default_printer_paper(company=company, branch=branch)
        branch = branch or resolved_branch or (printer.branch_id if printer else False)
        requested_paper = self._ickab_requested_paper(data)
        paper = paper or requested_paper or default_paper
        printer = printer or default_printer
        branch = branch or (printer.branch_id if printer else False)
        if printer and paper and not self._ickab_printer_supports_paper(printer, paper):
            printer = False
        copies = int(copies or default_copies or 1)
        if not printer:
            raise UserError(_("No existe una impresora configurada para el reporte %s.") % self.display_name)
        if printer.company_id != company:
            raise UserError(_("La impresora seleccionada pertenece a otra compañía."))
        if paper and printer.paper_ids and paper not in printer.paper_ids:
            raise UserError(_("El papel %s no está permitido en %s.") % (paper.display_name, printer.display_name))

        res_ids = self._ickab_normalize_res_ids(res_ids)
        payload_type, payload = self._ickab_render_payload(res_ids=res_ids, data=data or {}, printer=printer)
        source_record = self.env[self.model].browse(res_ids[0]).exists() if self.model and len(res_ids) == 1 else None
        job = self.env["ickab.print.job"].enqueue(
            printer=printer,
            payload_type=payload_type,
            payload=payload,
            paper=paper,
            copies=copies,
            source_record=source_record,
            report=self,
            filename=self._ickab_filename(payload_type),
            branch=branch,
        )
        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "title": _("Trabajo enviado a impresión"),
                "message": _("%s fue enviado a %s como %s.") % (job.name, printer.display_name, payload_type.upper()),
                "type": "success",
                "sticky": False,
                "next": {"type": "ir.actions.act_window_close"},
            },
        }

    def _ickab_open_print_wizard(self, *, res_ids=None, data=None):
        self.ensure_one()
        data = data or {}
        printer, fallback_paper, copies, branch = self._ickab_default_printer_paper()
        requested_paper = self._ickab_requested_paper(data)
        paper = requested_paper or fallback_paper

        # El formato elegido por el usuario en el documento manda sobre cualquier
        # papel predeterminado de la compañía o de la impresora.
        paper_locked = bool(requested_paper)
        if printer and not self._ickab_printer_supports_paper(printer, paper):
            printer = False

        if not printer:
            assigned = self.env["ickab.print.assignment"].assigned_printers(
                self.ickab_document_kind, user=self.env.user, company=self.env.company, branch=branch
            )
            candidates = assigned or self.env["ickab.print.printer"].search([
                ("company_id", "=", self.env.company.id),
                ("branch_id", "=", branch.id if branch else False),
                ("printer_type", "=", self.ickab_document_kind),
                ("active", "=", True),
            ])
            candidates = candidates.filtered(lambda item: self._ickab_printer_supports_paper(item, paper))
            if len(candidates) == 1:
                printer = candidates

        context = dict(self.env.context)
        context.update({
            "default_report_id": self.id,
            "default_res_model": self.model,
            "default_res_ids_json": json.dumps(self._ickab_normalize_res_ids(res_ids)),
            "default_report_data_json": json.dumps(data, default=str),
            "default_document_kind": self.ickab_document_kind,
            "default_printer_id": printer.id if printer else False,
            "default_paper_id": paper.id if paper else False,
            "default_paper_locked": paper_locked,
            "default_copies": copies or 1,
            "default_company_id": self.env.company.id,
            "default_branch_id": branch.id if branch else False,
        })
        return {
            "type": "ir.actions.act_window",
            "name": _("Impresión directa"),
            "res_model": "ickab.direct.print.wizard",
            "view_mode": "form",
            "view_id": self.env.ref("ickab_direct_print.view_ickab_direct_print_wizard_form").id,
            "target": "new",
            "context": context,
        }

    def report_action(self, docids, data=None, config=True):
        self.ensure_one()
        if self.env.context.get("ickab_skip_direct_print"):
            return super().report_action(docids, data=data, config=config)
        company = self.env.company
        if not self.env.user.has_group("ickab_direct_print.group_direct_print_user"):
            return super().report_action(docids, data=data, config=config)
        if not company.ickab_direct_print_enabled or self.ickab_print_mode == "standard":
            return super().report_action(docids, data=data, config=config)

        res_ids = self._ickab_normalize_res_ids(docids)
        if self.ickab_print_mode == "ask":
            return self._ickab_open_print_wizard(res_ids=res_ids, data=data or {})

        printer, paper, copies, branch = self._ickab_default_printer_paper()
        requested_paper = self._ickab_requested_paper(data or {})
        if requested_paper:
            paper = requested_paper
            if printer and not self._ickab_printer_supports_paper(printer, paper):
                printer = False
        if not printer and self.ickab_fallback_download:
            return super().report_action(docids, data=data, config=config)
        return self._ickab_enqueue_direct_print(
            res_ids=res_ids,
            data=data or {},
            printer=printer,
            paper=paper,
            copies=copies,
            branch=branch,
        )

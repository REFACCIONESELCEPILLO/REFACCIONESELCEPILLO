# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class IckabPrintBranch(models.Model):
    _name = "ickab.print.branch"
    _description = "ICKAB Print Branch"
    _order = "company_id, name"

    name = fields.Char(string="Sucursal", required=True)
    code = fields.Char(string="Código", index=True)
    company_id = fields.Many2one(
        "res.company", string="Compañía", required=True,
        default=lambda self: self.env.company, index=True,
    )
    active = fields.Boolean(default=True)
    notes = fields.Text(string="Notas")

    host_link_ids = fields.One2many("ickab.print.host.branch", "branch_id", string="Equipos / Agentes")
    user_line_ids = fields.One2many("ickab.print.user.branch", "branch_id", string="Usuarios habilitados")
    assignment_ids = fields.One2many("ickab.print.assignment", "branch_id", string="Asignaciones")

    default_label_printer_id = fields.Many2one(
        "ickab.print.printer", string="Impresora de etiquetas predeterminada",
        domain="[('branch_id', '=', id), ('printer_type', '=', 'label'), ('active', '=', True)]",
    )
    default_ticket_printer_id = fields.Many2one(
        "ickab.print.printer", string="Impresora de tickets predeterminada",
        domain="[('branch_id', '=', id), ('printer_type', '=', 'ticket'), ('active', '=', True)]",
    )
    default_document_printer_id = fields.Many2one(
        "ickab.print.printer", string="Impresora de documentos predeterminada",
        domain="[('branch_id', '=', id), ('printer_type', '=', 'document'), ('active', '=', True)]",
    )
    default_label_paper_id = fields.Many2one(
        "ickab.print.paper", string="Papel de etiquetas predeterminado",
        domain="['|', ('company_id', '=', False), ('company_id', '=', company_id), ('category', '=', 'label')]",
    )
    default_ticket_paper_id = fields.Many2one(
        "ickab.print.paper", string="Papel de tickets predeterminado",
        domain="['|', ('company_id', '=', False), ('company_id', '=', company_id), ('category', '=', 'ticket')]",
    )
    default_document_paper_id = fields.Many2one(
        "ickab.print.paper", string="Papel de documentos predeterminado",
        domain="['|', ('company_id', '=', False), ('company_id', '=', company_id), ('category', '=', 'document')]",
    )

    _sql_constraints = [
        ("company_code_unique", "unique(company_id, code)", "El código de sucursal debe ser único por compañía."),
    ]

    @api.constrains(
        "default_label_printer_id", "default_ticket_printer_id", "default_document_printer_id"
    )
    def _check_default_printers(self):
        for branch in self:
            pairs = (
                (branch.default_label_printer_id, "label"),
                (branch.default_ticket_printer_id, "ticket"),
                (branch.default_document_printer_id, "document"),
            )
            for printer, kind in pairs:
                if not printer:
                    continue
                if printer.company_id != branch.company_id:
                    raise ValidationError(_("La impresora predeterminada pertenece a otra compañía."))
                if printer.branch_id != branch:
                    raise ValidationError(_("La impresora predeterminada debe pertenecer a la misma sucursal."))
                if printer.printer_type != kind:
                    raise ValidationError(_("El tipo de la impresora predeterminada no coincide con su uso."))

    def default_printer_for(self, document_kind):
        self.ensure_one()
        return {
            "label": self.default_label_printer_id,
            "ticket": self.default_ticket_printer_id,
            "document": self.default_document_printer_id,
        }.get(document_kind, self.env["ickab.print.printer"])

    def default_paper_for(self, document_kind):
        self.ensure_one()
        return {
            "label": self.default_label_paper_id,
            "ticket": self.default_ticket_paper_id,
            "document": self.default_document_paper_id,
        }.get(document_kind, self.env["ickab.print.paper"])

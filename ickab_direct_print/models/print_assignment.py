# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


DOCUMENT_KIND_SELECTION = [
    ("label", "Etiqueta"),
    ("ticket", "Ticket"),
    ("document", "Documento"),
]


class IckabPrintAssignment(models.Model):
    _name = "ickab.print.assignment"
    _description = "ICKAB Print Assignment"
    _order = "branch_id, user_id, document_kind, priority, id"

    name = fields.Char(string="Descripción", compute="_compute_name", store=True)
    active = fields.Boolean(default=True)
    priority = fields.Integer(default=10, help="Un número menor tiene mayor prioridad.")
    is_default = fields.Boolean(
        string="Predeterminada",
        default=True,
        help="Cuando el usuario tiene varias impresoras del mismo tipo en una sucursal, ésta se selecciona primero.",
    )
    company_id = fields.Many2one(
        "res.company", string="Compañía", required=True,
        default=lambda self: self.env.company, index=True,
    )
    branch_id = fields.Many2one(
        "ickab.print.branch", string="Sucursal", required=True, ondelete="cascade", index=True,
        domain="[('company_id', '=', company_id), ('active', '=', True)]",
    )
    user_id = fields.Many2one(
        "res.users", string="Usuario", required=True, ondelete="cascade", index=True,
        domain="[('company_ids', 'in', company_id)]",
    )
    document_kind = fields.Selection(
        DOCUMENT_KIND_SELECTION, string="Tipo de impresión", required=True, index=True,
    )
    printer_id = fields.Many2one(
        "ickab.print.printer", string="Impresora", required=True, ondelete="cascade", index=True,
        domain="[('company_id', '=', company_id), ('branch_id', '=', branch_id), ('printer_type', '=', document_kind), ('active', '=', True)]",
    )
    host_id = fields.Many2one(related="printer_id.host_id", string="Equipo / Agente", store=True, readonly=True)
    paper_id = fields.Many2one(
        "ickab.print.paper", string="Papel predeterminado",
        domain="['|', ('company_id', '=', False), ('company_id', '=', company_id), ('category', '=', document_kind)]",
    )
    copies = fields.Integer(string="Copias", default=1, required=True)
    notes = fields.Char(string="Notas")

    @api.depends("user_id", "branch_id", "document_kind", "printer_id")
    def _compute_name(self):
        labels = dict(DOCUMENT_KIND_SELECTION)
        for assignment in self:
            parts = [
                assignment.user_id.name,
                assignment.branch_id.name,
                labels.get(assignment.document_kind),
                assignment.printer_id.name,
            ]
            assignment.name = " / ".join(part for part in parts if part)

    @api.constrains("copies")
    def _check_copies(self):
        for assignment in self:
            if assignment.copies < 1:
                raise ValidationError(_("El número de copias debe ser al menos 1."))

    @api.constrains("company_id", "branch_id", "user_id", "document_kind", "printer_id", "paper_id")
    def _check_consistency(self):
        for assignment in self:
            if assignment.branch_id.company_id != assignment.company_id:
                raise ValidationError(_("La sucursal pertenece a otra compañía."))
            if assignment.company_id not in assignment.user_id.company_ids:
                raise ValidationError(_("El usuario no tiene acceso a la compañía seleccionada."))
            access_lines = self.env["ickab.print.user.branch"].search([
                ("user_id", "=", assignment.user_id.id),
                ("company_id", "=", assignment.company_id.id),
                ("active", "=", True),
            ])
            if access_lines and assignment.branch_id not in access_lines.mapped("branch_id"):
                raise ValidationError(_(
                    "La sucursal no está habilitada para este usuario en ICKAB Direct Print."
                ))
            if assignment.printer_id.company_id != assignment.company_id:
                raise ValidationError(_("La impresora pertenece a otra compañía."))
            if assignment.printer_id.branch_id != assignment.branch_id:
                raise ValidationError(_("La impresora debe pertenecer a la sucursal seleccionada."))
            if assignment.printer_id.printer_type != assignment.document_kind:
                raise ValidationError(_("El tipo de impresora no coincide con el tipo de impresión."))
            if assignment.paper_id and assignment.printer_id.paper_ids and assignment.paper_id not in assignment.printer_id.paper_ids:
                raise ValidationError(_("El papel seleccionado no está permitido para la impresora."))

    @api.constrains("is_default", "active", "company_id", "branch_id", "user_id", "document_kind")
    def _check_single_default(self):
        for assignment in self.filtered(lambda a: a.active and a.is_default):
            other = self.search_count([
                ("id", "!=", assignment.id),
                ("active", "=", True),
                ("is_default", "=", True),
                ("company_id", "=", assignment.company_id.id),
                ("branch_id", "=", assignment.branch_id.id),
                ("user_id", "=", assignment.user_id.id),
                ("document_kind", "=", assignment.document_kind),
            ])
            if other:
                raise ValidationError(_(
                    "Sólo puede existir una impresora predeterminada por usuario, sucursal y tipo de impresión."
                ))

    @api.model
    def resolve_assignment(self, document_kind, *, user=None, company=None, branch=None):
        user = user or self.env.user
        company = company or self.env.company
        if not branch:
            branch = user._ickab_resolve_print_branch(company)
        if not branch or branch.company_id != company:
            return self.browse()
        return self.search([
            ("active", "=", True),
            ("company_id", "=", company.id),
            ("branch_id", "=", branch.id),
            ("user_id", "=", user.id),
            ("document_kind", "=", document_kind),
        ], order="is_default desc, priority, id", limit=1)

    @api.model
    def assigned_printers(self, document_kind, *, user=None, company=None, branch=None):
        user = user or self.env.user
        company = company or self.env.company
        if not branch:
            return self.env["ickab.print.printer"]
        assignments = self.search([
            ("active", "=", True),
            ("company_id", "=", company.id),
            ("branch_id", "=", branch.id),
            ("user_id", "=", user.id),
            ("document_kind", "=", document_kind),
        ], order="is_default desc, priority, id")
        return assignments.mapped("printer_id").filtered(lambda p: p.active)

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class IckabPrintProfile(models.Model):
    _name = "ickab.print.profile"
    _description = "ICKAB Print Profile"
    _order = "priority, name"

    name = fields.Char(required=True)
    active = fields.Boolean(default=True)
    priority = fields.Integer(default=10, help="Un número menor tiene mayor prioridad.")
    company_id = fields.Many2one(
        "res.company",
        required=True,
        default=lambda self: self.env.company,
        index=True,
    )
    document_kind = fields.Selection(
        [("label", "Etiqueta"), ("ticket", "Ticket"), ("document", "Documento")],
        required=True,
        index=True,
    )
    report_id = fields.Many2one("ir.actions.report", string="Reporte")
    user_id = fields.Many2one("res.users", string="Usuario", domain="[('company_ids', 'in', company_id)]")
    model_name = fields.Char(
        string="Modelo técnico",
        help="Opcional. Ejemplo: sale.order, account.move o product.product.",
    )
    printer_id = fields.Many2one(
        "ickab.print.printer",
        required=True,
        domain="[('company_id', '=', company_id), ('printer_type', '=', document_kind), ('active', '=', True)]",
    )
    paper_id = fields.Many2one(
        "ickab.print.paper",
        required=True,
        domain="['|', ('company_id', '=', False), ('company_id', '=', company_id)]",
    )
    copies = fields.Integer(default=1, required=True)
    direct_print = fields.Boolean(string="Impresión directa", default=True)
    fallback_download = fields.Boolean(string="Permitir descarga si falla", default=True)

    @api.constrains("copies")
    def _check_copies(self):
        for profile in self:
            if profile.copies < 1:
                raise ValidationError(_("El número de copias debe ser al menos 1."))

    @api.constrains("printer_id", "paper_id", "document_kind")
    def _check_compatibility(self):
        for profile in self:
            if profile.printer_id and profile.printer_id.printer_type != profile.document_kind:
                raise ValidationError(_("El tipo de impresora no coincide con el tipo de documento."))
            if profile.printer_id.paper_ids and profile.paper_id not in profile.printer_id.paper_ids:
                raise ValidationError(_("El papel seleccionado no está permitido en la impresora."))

    @api.model
    def resolve_profile(self, document_kind, report=None, user=None, company=None, model_name=None, branch=None):
        company = company or self.env.company
        user = user or self.env.user
        branch = branch or user._ickab_resolve_print_branch(company)
        domain = [
            ("active", "=", True),
            ("company_id", "=", company.id),
            ("document_kind", "=", document_kind),
        ]
        profiles = self.search(domain, order="priority, id")
        best = self.browse()
        best_score = -1
        for profile in profiles:
            if profile.printer_id.branch_id and branch and profile.printer_id.branch_id != branch:
                continue
            if profile.user_id and profile.user_id != user:
                continue
            if profile.report_id and (not report or profile.report_id != report):
                continue
            if profile.model_name and profile.model_name != (model_name or ""):
                continue
            score = 0
            score += 4 if profile.user_id else 0
            score += 3 if profile.report_id else 0
            score += 2 if profile.model_name else 0
            if score > best_score:
                best = profile
                best_score = score
        return best

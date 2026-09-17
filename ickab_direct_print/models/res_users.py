# -*- coding: utf-8 -*-

from odoo import fields, models


class ResUsers(models.Model):
    _inherit = "res.users"

    # Sólo relaciones One2many. No se agrega ninguna columna a res_users.
    # Esto evita bloquear el arranque al desplegar una versión nueva antes de -u.
    ickab_print_branch_line_ids = fields.One2many(
        "ickab.print.user.branch", "user_id", string="Sucursales de impresión"
    )
    ickab_print_assignment_ids = fields.One2many(
        "ickab.print.assignment", "user_id", string="Asignaciones de impresión"
    )

    def _ickab_available_print_branches(self, company=None):
        self.ensure_one()
        company = company or self.env.company
        lines = self.env["ickab.print.user.branch"].search([
            ("user_id", "=", self.id),
            ("company_id", "=", company.id),
            ("active", "=", True),
            ("branch_id.active", "=", True),
        ], order="is_default desc, id")
        if lines:
            return lines.mapped("branch_id")

        # Compatibilidad: mientras el administrador no limite explícitamente al
        # usuario, puede trabajar con las sucursales activas de su compañía.
        return self.env["ickab.print.branch"].search([
            ("company_id", "=", company.id),
            ("active", "=", True),
        ], order="name, id")

    def _ickab_resolve_print_branch(self, company=None):
        self.ensure_one()
        company = company or self.env.company
        default_line = self.env["ickab.print.user.branch"].search([
            ("user_id", "=", self.id),
            ("company_id", "=", company.id),
            ("active", "=", True),
            ("is_default", "=", True),
            ("branch_id.active", "=", True),
        ], limit=1)
        if default_line:
            return default_line.branch_id
        return self._ickab_available_print_branches(company)[:1]

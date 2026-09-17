# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class IckabPrintUserBranch(models.Model):
    _name = "ickab.print.user.branch"
    _description = "ICKAB Print User Branch Access"
    _order = "user_id, company_id, is_default desc, branch_id"

    active = fields.Boolean(default=True)
    user_id = fields.Many2one(
        "res.users", string="Usuario", required=True, ondelete="cascade", index=True,
    )
    branch_id = fields.Many2one(
        "ickab.print.branch", string="Sucursal", required=True, ondelete="cascade", index=True,
        domain="[('company_id', 'in', user_company_ids), ('active', '=', True)]",
    )
    company_id = fields.Many2one(
        related="branch_id.company_id", string="Compañía", store=True, readonly=True, index=True,
    )
    user_company_ids = fields.Many2many(
        related="user_id.company_ids", string="Compañías del usuario", readonly=True,
    )
    is_default = fields.Boolean(
        string="Sucursal predeterminada",
        help="Se usa automáticamente al abrir el asistente de impresión para esta compañía.",
    )
    notes = fields.Char(string="Notas")

    _sql_constraints = [
        (
            "user_branch_unique",
            "unique(user_id, branch_id)",
            "La sucursal ya está asignada a este usuario.",
        ),
    ]

    @api.constrains("user_id", "branch_id")
    def _check_company_access(self):
        for line in self:
            if line.branch_id.company_id not in line.user_id.company_ids:
                raise ValidationError(_(
                    "El usuario no tiene acceso a la compañía de la sucursal seleccionada."
                ))

    @api.constrains("is_default", "active", "user_id", "company_id")
    def _check_single_default(self):
        for line in self.filtered(lambda item: item.active and item.is_default):
            count = self.search_count([
                ("id", "!=", line.id),
                ("active", "=", True),
                ("is_default", "=", True),
                ("user_id", "=", line.user_id.id),
                ("company_id", "=", line.company_id.id),
            ])
            if count:
                raise ValidationError(_(
                    "Sólo puede existir una sucursal predeterminada por usuario y compañía."
                ))


class IckabPrintHostBranch(models.Model):
    """Relación 1:1 host -> sucursal sin alterar la tabla histórica del host.

    Mantener esta relación en una tabla propia permite desplegar código nuevo sobre una
    base con la versión anterior sin provocar UndefinedColumn durante el arranque.
    """

    _name = "ickab.print.host.branch"
    _description = "ICKAB Print Host Branch"
    _order = "branch_id, host_id"

    host_id = fields.Many2one(
        "ickab.print.host", string="Equipo / Agente", required=True,
        ondelete="cascade", index=True,
    )
    branch_id = fields.Many2one(
        "ickab.print.branch", string="Sucursal", required=True,
        ondelete="cascade", index=True,
    )
    company_id = fields.Many2one(
        related="host_id.company_id", string="Compañía", store=True, readonly=True, index=True,
    )
    hostname = fields.Char(related="host_id.hostname", string="Nombre detectado", readonly=True)
    platform_type = fields.Selection(related="host_id.platform_type", string="Plataforma", readonly=True)
    state = fields.Selection(related="host_id.state", string="Estado", readonly=True)
    printer_count = fields.Integer(related="host_id.printer_count", string="Impresoras", readonly=True)
    last_seen = fields.Datetime(related="host_id.last_seen", string="Última conexión", readonly=True)

    _sql_constraints = [
        (
            "host_unique_branch",
            "unique(host_id)",
            "Cada equipo/agente sólo puede pertenecer a una sucursal.",
        ),
    ]

    @api.constrains("host_id", "branch_id")
    def _check_company(self):
        for link in self:
            if link.host_id.company_id != link.branch_id.company_id:
                raise ValidationError(_(
                    "El equipo y la sucursal deben pertenecer a la misma compañía."
                ))


class IckabPrintJobContext(models.Model):
    """Contexto multisucursal del trabajo sin alterar la tabla histórica de jobs."""

    _name = "ickab.print.job.context"
    _description = "ICKAB Print Job Branch Context"

    job_id = fields.Many2one(
        "ickab.print.job", string="Trabajo", required=True,
        ondelete="cascade", index=True,
    )
    branch_id = fields.Many2one(
        "ickab.print.branch", string="Sucursal", required=True,
        ondelete="restrict", index=True,
    )
    company_id = fields.Many2one(
        related="job_id.company_id", string="Compañía", store=True, readonly=True, index=True,
    )

    _sql_constraints = [
        (
            "job_unique_context",
            "unique(job_id)",
            "El trabajo ya tiene un contexto de sucursal.",
        ),
    ]

    @api.constrains("job_id", "branch_id")
    def _check_company(self):
        for context in self:
            if context.job_id.company_id != context.branch_id.company_id:
                raise ValidationError(_(
                    "El trabajo y la sucursal deben pertenecer a la misma compañía."
                ))

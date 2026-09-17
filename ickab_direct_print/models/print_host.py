import secrets
import uuid
from datetime import timedelta

from odoo import api, fields, models, _
from odoo.exceptions import UserError


class IckabPrintHost(models.Model):
    _name = "ickab.print.host"
    _description = "ICKAB Print Host"
    _order = "name"

    name = fields.Char(string="Nombre del equipo", required=True)
    uuid = fields.Char(
        string="Identificador técnico (UUID)",
        required=True,
        copy=False,
        readonly=True,
        default=lambda self: str(uuid.uuid4()),
        index=True,
        help="Identificador interno del agente. Normalmente no necesitas capturarlo manualmente.",
    )
    api_token = fields.Char(
        string="Token técnico del agente",
        required=True,
        copy=False,
        readonly=True,
        default=lambda self: secrets.token_urlsafe(32),
        groups="ickab_direct_print.group_direct_print_manager",
        help="Credencial secreta usada por el agente. Para una instalación normal usa el Código de instalación.",
    )
    pairing_code = fields.Char(
        string="Código de instalación",
        readonly=True,
        copy=False,
        help="Código temporal que se captura en el instalador de Windows. Evita copiar UUID y Token manualmente.",
    )
    pairing_expires_at = fields.Datetime(
        string="Código válido hasta",
        readonly=True,
        copy=False,
    )
    company_id = fields.Many2one(
        "res.company",
        string="Compañía",
        required=True,
        default=lambda self: self.env.company,
        index=True,
    )
    branch_id = fields.Many2one(
        "ickab.print.branch",
        string="Sucursal",
        compute="_compute_branch_id",
        inverse="_inverse_branch_id",
        search="_search_branch_id",
        domain="[('company_id', '=', company_id), ('active', '=', True)]",
        help="Sucursal física donde está instalado este equipo/agente. La relación se guarda en una tabla ICKAB independiente.",
    )
    active = fields.Boolean(string="Activo", default=True)
    state = fields.Selection(
        [
            ("offline", "Fuera de línea"),
            ("online", "En línea"),
            ("error", "Error"),
        ],
        string="Estado",
        default="offline",
        required=True,
        readonly=True,
        index=True,
    )
    last_seen = fields.Datetime(string="Última conexión", readonly=True)
    agent_version = fields.Char(string="Versión del agente", readonly=True)
    platform = fields.Char(string="Sistema detectado", readonly=True)
    platform_type = fields.Selection(
        [("windows", "Windows"), ("linux", "Linux"), ("android", "Android"), ("other", "Otro")],
        string="Plataforma detectada",
        default="other",
        readonly=True,
        help="Se completa automáticamente cuando el agente se conecta por primera vez.",
    )
    supports_usb = fields.Boolean(string="USB", readonly=True)
    supports_tcp = fields.Boolean(string="Red TCP/IP", readonly=True)
    supports_bluetooth_spp = fields.Boolean(string="Bluetooth Classic / SPP", readonly=True)
    supports_bluetooth_ble = fields.Boolean(string="Bluetooth LE", readonly=True)
    supports_android_print = fields.Boolean(string="Android Print Service", readonly=True)
    capabilities_json = fields.Text(string="Capacidades técnicas del agente", readonly=True)
    hostname = fields.Char(string="Nombre detectado del equipo", readonly=True)
    ip_address = fields.Char(string="IP informativa", readonly=True)
    notes = fields.Text(string="Notas")
    printer_ids = fields.One2many("ickab.print.printer", "host_id", string="Impresoras")
    printer_count = fields.Integer(string="Impresoras", compute="_compute_printer_count")

    _sql_constraints = [
        ("uuid_unique", "unique(uuid)", "El UUID del host debe ser único."),
        ("api_token_unique", "unique(api_token)", "El token del agente debe ser único."),
    ]

    @api.depends("printer_ids")
    def _compute_printer_count(self):
        for host in self:
            host.printer_count = len(host.printer_ids)

    def _compute_branch_id(self):
        links = self.env["ickab.print.host.branch"].search([("host_id", "in", self.ids)]) if self.ids else self.env["ickab.print.host.branch"]
        by_host = {link.host_id.id: link.branch_id for link in links}
        for host in self:
            host.branch_id = by_host.get(host.id, False)

    def _inverse_branch_id(self):
        Link = self.env["ickab.print.host.branch"]
        for host in self:
            if not host.id:
                continue
            link = Link.search([("host_id", "=", host.id)], limit=1)
            branch = host.branch_id
            if branch:
                vals = {"host_id": host.id, "branch_id": branch.id}
                if link:
                    if link.branch_id != branch:
                        link.write({"branch_id": branch.id})
                else:
                    Link.create(vals)
            elif link:
                link.unlink()
            host.invalidate_recordset(["branch_id"])

    @api.model
    def _search_branch_id(self, operator, value):
        Link = self.env["ickab.print.host.branch"]
        all_linked = Link.search([]).mapped("host_id").ids

        if operator in ("=", "in"):
            if operator == "=" and value is False:
                return [("id", "not in", all_linked)]
            if operator == "in" and not value:
                return [("id", "=", 0)]
            links = Link.search([("branch_id", operator, value)])
            return [("id", "in", links.mapped("host_id").ids)]

        if operator in ("!=", "not in"):
            if operator == "!=" and value is False:
                return [("id", "in", all_linked)]
            positive = "=" if operator == "!=" else "in"
            links = Link.search([("branch_id", positive, value)])
            return [("id", "not in", links.mapped("host_id").ids)]

        # Many2one branch filtering only needs equality style operators in Direct Print.
        return [("id", "=", 0)]

    def action_generate_pairing_code(self):
        self.ensure_one()
        now = fields.Datetime.now()
        Host = self.env["ickab.print.host"]
        for attempt in range(20):
            code = f"{secrets.randbelow(100000000):08d}"
            if not Host.search_count([
                ("id", "!=", self.id),
                ("pairing_code", "=", code),
                ("pairing_expires_at", ">", now),
            ]):
                break
        else:
            raise UserError(_("No fue posible generar un código de instalación. Intenta nuevamente."))
        self.write({
            "pairing_code": code,
            "pairing_expires_at": now + timedelta(minutes=15),
        })
        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "title": _("Código de instalación listo"),
                "message": _("Captura el código %s en el instalador de ICKAB Print Agent. Es válido durante 15 minutos.") % code,
                "type": "success",
                "sticky": True,
            },
        }

    def action_regenerate_token(self):
        self.ensure_one()
        self.write({
            "api_token": secrets.token_urlsafe(32),
            "pairing_code": False,
            "pairing_expires_at": False,
        })
        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "title": _("Token regenerado"),
                "message": _("El agente actual dejará de autenticarse hasta volver a configurarlo."),
                "type": "warning",
                "sticky": True,
            },
        }

    def action_view_printers(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": _("Impresoras"),
            "res_model": "ickab.print.printer",
            "view_mode": "list,form",
            "domain": [("host_id", "=", self.id)],
            "context": {"default_host_id": self.id, "default_company_id": self.company_id.id},
        }

    @api.model
    def _cron_mark_offline(self):
        threshold = fields.Datetime.now() - timedelta(minutes=2)
        hosts = self.search([
            ("state", "=", "online"),
            "|",
            ("last_seen", "=", False),
            ("last_seen", "<", threshold),
        ])
        if hosts:
            hosts.write({"state": "offline"})
            hosts.mapped("printer_ids").filtered(lambda p: p.source == "discovered").write({"state": "unavailable"})

# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError

from .print_compatibility_profile import LANGUAGE_SELECTION, TRANSPORT_SELECTION


class IckabPrintPrinter(models.Model):
    _name = "ickab.print.printer"
    _description = "ICKAB Printer"
    _order = "host_id, name"

    name = fields.Char(required=True)
    company_id = fields.Many2one("res.company", required=True, default=lambda self: self.env.company, index=True)
    host_id = fields.Many2one(
        "ickab.print.host", required=True, ondelete="cascade",
        domain="[('company_id', '=', company_id)]", index=True,
    )
    active = fields.Boolean(default=True)
    source = fields.Selection(
        [("discovered", "Detectada por agente"), ("manual", "Configuración manual")],
        default="manual", required=True,
    )
    system_uid = fields.Char(string="ID del sistema", copy=False, index=True)
    system_name = fields.Char(string="Nombre en sistema operativo")
    device_uri = fields.Char(string="URI / dispositivo")
    is_system_default = fields.Boolean(string="Predeterminada del sistema", readonly=True)
    printer_type = fields.Selection(
        [("label", "Etiquetas"), ("ticket", "Tickets"), ("document", "Documentos")],
        string="Tipo", required=True, default="document", index=True,
    )
    transport = fields.Selection(TRANSPORT_SELECTION, required=True, default="windows_spooler")
    language = fields.Selection(LANGUAGE_SELECTION, required=True, default="pdf")
    compatibility_profile_id = fields.Many2one(
        "ickab.print.compatibility.profile",
        string="Perfil de compatibilidad",
        domain="[('active', '=', True)]",
        help="Perfil de fabricante/modelo aplicado a esta impresora.",
    )
    suggested_compatibility_profile_id = fields.Many2one(
        "ickab.print.compatibility.profile",
        string="Compatibilidad sugerida",
        compute="_compute_suggested_compatibility_profile_id",
        help="Sugerencia por nombre/modelo. Nunca cambia la configuración automáticamente.",
    )
    compatibility_validation_status = fields.Selection(
        related="compatibility_profile_id.validation_status",
        string="Validación del perfil",
        readonly=True,
    )
    compatibility_notes = fields.Text(
        related="compatibility_profile_id.notes",
        string="Notas del perfil",
        readonly=True,
    )
    state = fields.Selection(
        [("unavailable", "No disponible"), ("ready", "Disponible"), ("error", "Error")],
        default="unavailable", readonly=True, required=True, index=True,
    )
    last_seen = fields.Datetime(readonly=True)
    dpi = fields.Selection(
        [("203", "203 dpi"), ("300", "300 dpi"), ("600", "600 dpi"), ("na", "No aplica")],
        default="na", string="Resolución",
    )
    network_host = fields.Char(string="IP / Host de red")
    network_port = fields.Integer(string="Puerto TCP", default=9100)
    bluetooth_address = fields.Char(string="Dirección Bluetooth")
    bluetooth_name = fields.Char(string="Nombre Bluetooth")
    bluetooth_spp_uuid = fields.Char(
        string="UUID SPP",
        default="00001101-0000-1000-8000-00805F9B34FB",
        help="UUID estándar Serial Port Profile. Puede cambiarse si el fabricante usa uno propio.",
    )
    ble_service_uuid = fields.Char(string="BLE Service UUID")
    ble_characteristic_uuid = fields.Char(string="BLE Characteristic UUID")
    usb_vendor_id = fields.Char(string="USB Vendor ID")
    usb_product_id = fields.Char(string="USB Product ID")
    paper_ids = fields.Many2many(
        "ickab.print.paper", "ickab_print_printer_paper_rel", "printer_id", "paper_id",
        string="Papeles permitidos",
        domain="['|', ('company_id', '=', False), ('company_id', '=', company_id)]",
    )
    default_paper_id = fields.Many2one(
        "ickab.print.paper", string="Papel predeterminado", domain="[('id', 'in', paper_ids)]"
    )
    capabilities_json = fields.Text(string="Capacidades reportadas", readonly=True)
    last_error = fields.Text(readonly=True)

    _sql_constraints = [
        ("host_system_uid_unique", "unique(host_id, system_uid)", "El identificador de impresora debe ser único dentro del host."),
    ]

    @api.depends("name", "system_name")
    def _compute_suggested_compatibility_profile_id(self):
        profiles = self.env["ickab.print.compatibility.profile"].search([("active", "=", True)])
        for printer in self:
            value = " ".join(filter(None, [printer.name, printer.system_name]))
            printer.suggested_compatibility_profile_id = next(
                (profile for profile in profiles if profile.matches_printer_name(value)),
                False,
            )

    @api.constrains("transport", "network_host", "network_port", "bluetooth_address")
    def _check_transport_configuration(self):
        for printer in self:
            if printer.transport == "tcp_raw":
                if not printer.network_host:
                    raise ValidationError(_("Una impresora TCP/IP RAW requiere IP o nombre de host."))
                if not 1 <= (printer.network_port or 0) <= 65535:
                    raise ValidationError(_("El puerto TCP debe estar entre 1 y 65535."))
            if printer.transport in ("bluetooth_spp", "bluetooth_ble") and not printer.bluetooth_address:
                raise ValidationError(_("Una impresora Bluetooth requiere una dirección/MAC de dispositivo."))

    @api.constrains("default_paper_id", "paper_ids")
    def _check_default_paper(self):
        for printer in self:
            if printer.default_paper_id and printer.paper_ids and printer.default_paper_id not in printer.paper_ids:
                raise ValidationError(_("El papel predeterminado debe formar parte de los papeles permitidos."))

    @api.onchange("printer_type")
    def _onchange_printer_type(self):
        label_languages = ("zpl", "tspl", "epl", "cpcl")
        for printer in self:
            if printer.printer_type == "label" and printer.language == "pdf":
                printer.language = "zpl"
                if printer.dpi == "na":
                    printer.dpi = "203"
            elif printer.printer_type == "ticket" and printer.language == "pdf":
                printer.language = "escpos"
            elif printer.printer_type == "document" and printer.language in label_languages + ("escpos",):
                printer.language = "pdf"
                printer.dpi = "na"

    def action_apply_compatibility_profile(self):
        for printer in self:
            profile = printer.compatibility_profile_id or printer.suggested_compatibility_profile_id
            if not profile:
                raise UserError(_("No existe un perfil de compatibilidad seleccionado o sugerido."))
            # El transporte NO se modifica: describe la conexión física real (USB/red/etc.).
            printer.write({
                "compatibility_profile_id": profile.id,
                "printer_type": profile.printer_type,
                "language": profile.language,
                "dpi": profile.dpi,
            })
        return True

    def accepted_payload_types(self):
        """Tipos que una impresora puede recibir sin conversión de lenguaje."""
        self.ensure_one()
        mapping = {
            "zpl": {"zpl", "raw"},
            "tspl": {"tspl", "raw"},
            "epl": {"epl", "raw"},
            "escpos": {"escpos", "raw"},
            "cpcl": {"cpcl", "raw"},
            "pdf": {"pdf", "raw"},
            "image": {"image", "raw"},
            "raw": {"zpl", "tspl", "epl", "escpos", "cpcl", "pdf", "image", "raw"},
        }
        return mapping.get(self.language, {"raw"})

    def action_test_print(self):
        self.ensure_one()
        paper = self.default_paper_id

        if self.language == "zpl":
            payload = self._test_zpl(paper)
            return self.env["ickab.print.job"].enqueue(
                printer=self, payload_type="zpl", payload=payload,
                paper=paper, filename="ickab_test.zpl",
            ).action_open_job()

        if self.language == "tspl":
            payload = self._test_tspl(paper)
            return self.env["ickab.print.job"].enqueue(
                printer=self, payload_type="tspl", payload=payload,
                paper=paper, filename="ickab_test.tspl", mime_type="text/plain",
            ).action_open_job()

        if self.language == "epl":
            payload = self._test_epl(paper)
            return self.env["ickab.print.job"].enqueue(
                printer=self, payload_type="epl", payload=payload,
                paper=paper, filename="ickab_test.epl", mime_type="text/plain",
            ).action_open_job()

        if self.language == "escpos":
            raw = b"\x1b@\x1ba\x01ICKAB DIRECT PRINT\nPRUEBA DE IMPRESORA\n\n\x1dV\x00"
            return self.env["ickab.print.job"].enqueue(
                printer=self, payload_type="escpos", payload=raw,
                paper=paper, filename="ickab_test.bin",
            ).action_open_job()

        if self.language == "cpcl":
            raw = b"! 0 200 200 300 1\r\nTEXT 4 0 30 30 ICKAB DIRECT PRINT\r\nTEXT 4 0 30 80 PRUEBA CPCL\r\nFORM\r\nPRINT\r\n"
            return self.env["ickab.print.job"].enqueue(
                printer=self, payload_type="cpcl", payload=raw,
                paper=paper, filename="ickab_test.cpcl",
            ).action_open_job()

        raise UserError(_(
            "La prueba RAW automática está disponible para ZPL, TSPL/TSPL2, EPL/EPL2, ESC/POS y CPCL. "
            "Para PDF/Imagen utilice un reporte real mediante el driver del sistema operativo."
        ))

    def _resolved_dpi(self, paper=None):
        self.ensure_one()
        if self.dpi in ("203", "300", "600"):
            return int(self.dpi)
        if paper and paper.default_dpi in ("203", "300", "600"):
            return int(paper.default_dpi)
        return 203

    def _paper_geometry(self, paper=None):
        self.ensure_one()
        return (
            float(paper.width_mm if paper else 50.0),
            float(paper.height_mm if paper and paper.height_mm else 30.0),
            self._resolved_dpi(paper),
        )

    def _ickab_zpl_preamble(self, width_mm, height_mm, dpi=None):
        """Return the canonical ZPL physical label preamble for this printer."""
        self.ensure_one()
        dpi = int(dpi or self._resolved_dpi())
        dot = lambda mm: max(0, int(round(float(mm) * dpi / 25.4)))
        profile = self.compatibility_profile_id
        ref_x = int(profile.origin_x_dots if profile else 0)
        ref_y = int(profile.origin_y_dots if profile else 0)
        return "\n".join([
            "^XA", "^CI28", f"^PW{dot(width_mm)}", f"^LL{dot(height_mm)}",
            f"^LH{ref_x},{ref_y}", "^LT0", "^LS0",
        ]) + "\n"

    def _test_zpl(self, paper=None):
        width_mm, height_mm, dpi = self._paper_geometry(paper)
        dot = lambda mm: max(1, int(round(float(mm) * dpi / 25.4)))
        width, height = dot(width_mm), dot(height_mm)
        margin_x = max(10, int(width * 0.04))
        margin_y = max(8, int(height * 0.05))
        right = max(margin_x + 1, width - margin_x)
        bottom = max(margin_y + 1, height - margin_y)
        title_h = max(18, min(34, int(height * 0.12)))
        subtitle_h = max(14, min(26, int(height * 0.09)))
        return self._ickab_zpl_preamble(width_mm, height_mm, dpi=dpi) + "\n".join([
            f"^FO{margin_x},{margin_y}^GB{right - margin_x},{bottom - margin_y},2^FS",
            f"^FO{margin_x + 15},{margin_y + 20}^A0N,{title_h},{title_h}^FDICKAB DIRECT PRINT^FS",
            f"^FO{margin_x + 15},{margin_y + 65}^A0N,{subtitle_h},{subtitle_h}^FDPRUEBA ZPL {dpi} DPI^FS",
            "^XZ",
        ])

    def _ickab_tspl_preamble(self, width_mm, height_mm, paper=None, include_codepage=True):
        """Return the canonical TSPL media/setup preamble for this printer.

        Communication tests and real label renderers must use the same physical
        setup. This keeps SIZE/GAP/BLINE/DIRECTION/REFERENCE in one place and
        prevents the test path from behaving differently from a product label.
        """
        self.ensure_one()
        profile = self.compatibility_profile_id
        direction = (profile.label_direction if profile else "1") or "1"
        ref_x = int(profile.origin_x_dots if profile else 0)
        ref_y = int(profile.origin_y_dots if profile else 0)

        sensor_mode = getattr(paper, "sensor_mode", "gap") if paper else "gap"
        gap_mm = float(getattr(paper, "gap_mm", 2.0) if paper else 2.0)
        gap_offset = float(getattr(paper, "gap_offset_mm", 0.0) if paper else 0.0)
        if sensor_mode == "blackmark":
            media = f"BLINE {gap_mm:g} mm,{gap_offset:g} mm"
        elif sensor_mode == "continuous":
            media = "GAP 0 mm,0 mm"
        else:
            media = f"GAP {gap_mm:g} mm,{gap_offset:g} mm"

        lines = [
            f"SIZE {float(width_mm):g} mm,{float(height_mm):g} mm",
            media,
            f"DIRECTION {direction}",
            f"REFERENCE {ref_x},{ref_y}",
        ]
        if include_codepage:
            lines.append("CODEPAGE 850")
        return "\r\n".join(lines) + "\r\n"

    def _test_tspl(self, paper=None):
        width_mm, height_mm, dpi = self._paper_geometry(paper)
        dpmm = {203: 8, 300: 12, 600: 24}.get(dpi, max(1, int(round(dpi / 25.4))))
        width = max(1, int(round(width_mm * dpmm)))
        height = max(1, int(round(height_mm * dpmm)))
        margin = max(5, int(round(0.8 * dpmm)))
        right, bottom = max(margin + 1, width - margin), max(margin + 1, height - margin)
        payload = self._ickab_tspl_preamble(width_mm, height_mm, paper=paper)
        lines = [
            "CLS",
            f"BOX {margin},{margin},{right},{bottom},2",
            f'TEXT {max(margin + 15, int(width * 0.08))},{max(margin + 20, int(height * 0.18))},"3",0,1,1,"ICKAB DIRECT PRINT"',
            f'TEXT {max(margin + 15, int(width * 0.08))},{max(margin + 55, int(height * 0.43))},"2",0,1,1,"PRUEBA TSPL {dpi} DPI"',
            "PRINT 1,1",
            "",
        ]
        return payload + "\r\n".join(lines)

    def _test_epl(self, paper=None):
        width_mm, height_mm, dpi = self._paper_geometry(paper)
        dot = lambda mm: max(1, int(round(float(mm) * dpi / 25.4)))
        width, height = dot(width_mm), dot(height_mm)
        # EPL2: N limpia buffer, q define ancho y Q largo/gap; P1 imprime una etiqueta.
        return "\n".join([
            "N",
            f"q{width}",
            f"Q{height},16",
            'A30,30,0,3,1,1,N,"ICKAB DIRECT PRINT"',
            f'A30,80,0,2,1,1,N,"PRUEBA EPL {dpi} DPI"',
            "P1",
            "",
        ])

# -*- coding: utf-8 -*-
import re

from odoo import fields, models


LANGUAGE_SELECTION = [
    ("zpl", "ZPL / ZPL II"),
    ("tspl", "TSPL / TSPL2"),
    ("epl", "EPL / EPL2"),
    ("cpcl", "CPCL"),
    ("escpos", "ESC/POS"),
    ("starprnt", "StarPRNT / Star"),
    ("sbpl", "SATO SBPL"),
    ("dpl", "Datamax DPL"),
    ("ipl", "Intermec IPL"),
    ("fingerprint", "Intermec Fingerprint / Direct Protocol"),
    ("brother_raster", "Brother Raster / P-touch"),
    ("pcl", "HP PCL"),
    ("postscript", "PostScript"),
    ("pwg_raster", "PWG Raster"),
    ("pdf", "PDF / Driver"),
    ("image", "Imagen / Driver"),
    ("raw", "RAW genérico"),
]


TRANSPORT_SELECTION = [
    ("windows_raw", "Windows RAW"),
    ("tcp_raw", "TCP/IP RAW"),
    ("windows_spooler", "Windows Spooler"),
    ("cups", "CUPS"),
    ("bluetooth_spp", "Bluetooth Classic / SPP"),
    ("bluetooth_ble", "Bluetooth Low Energy"),
    ("android_print_service", "Android Print Service"),
    ("usb_otg", "Android USB OTG"),
]


class IckabPrintCompatibilityProfile(models.Model):
    _name = "ickab.print.compatibility.profile"
    _description = "ICKAB Printer Compatibility Profile"
    _order = "priority desc, manufacturer, model_name, name"

    name = fields.Char(string="Perfil", required=True)
    active = fields.Boolean(default=True)
    priority = fields.Integer(default=10)
    manufacturer = fields.Char(string="Fabricante")
    model_name = fields.Char(string="Modelo")
    name_pattern = fields.Char(
        string="Patrón de detección",
        help="Expresión regular aplicada al nombre detectado por el sistema operativo.",
    )
    printer_type = fields.Selection(
        [("label", "Etiquetas"), ("ticket", "Tickets"), ("document", "Documentos")],
        string="Tipo recomendado",
        default="label",
        required=True,
    )
    language = fields.Selection(
        LANGUAGE_SELECTION,
        string="Lenguaje recomendado",
        required=True,
        default="zpl",
    )
    dpi = fields.Selection(
        [("203", "203 dpi"), ("300", "300 dpi"), ("600", "600 dpi"), ("na", "No aplica")],
        string="Resolución recomendada",
        default="203",
        required=True,
    )

    label_direction = fields.Selection(
        [("0", "Dirección 0"), ("1", "Dirección 1")],
        string="Dirección nativa de etiqueta",
        default="1",
        required=True,
        help="Dirección usada por lenguajes de etiqueta como TSPL. Se aplica desde el perfil; no desde el diseño.",
    )
    origin_x_dots = fields.Integer(
        string="Ajuste X (dots)",
        default=0,
        help="Ajuste técnico de origen horizontal. Debe permanecer en 0 salvo validación física del modelo.",
    )
    origin_y_dots = fields.Integer(
        string="Ajuste Y (dots)",
        default=0,
        help="Ajuste técnico de origen vertical. Debe permanecer en 0 salvo validación física del modelo.",
    )
    tspl_bitmap_one_is_black = fields.Boolean(
        string="TSPL BITMAP: bit 1 imprime negro",
        default=True,
        help="Polaridad del comando BITMAP. Algunos compatibles invierten la polaridad respecto del comportamiento TSPL habitual.",
    )
    supports_inline_bitmap = fields.Boolean(
        string="Soporta BITMAP en línea",
        default=True,
        help="Permite al generador incluir gráficos pequeños (por ejemplo el logo) como BITMAP dentro del trabajo RAW.",
    )
    tspl_scalable_font0 = fields.Boolean(
        string="TSPL2: fuente 0 escalable",
        default=False,
        help=(
            "Actívalo sólo cuando el modelo/firmware confirme TSPL2 con la fuente interna 0. "
            "Permite respetar mejor la jerarquía tipográfica del layout (código, nombre y OEM)."
        ),
    )
    recommended_transport = fields.Selection(
        TRANSPORT_SELECTION,
        string="Transporte sugerido",
        help="Es una recomendación. Aplicar el perfil no cambia el transporte físico configurado.",
    )
    validation_status = fields.Selection(
        [
            ("unverified", "No validado"),
            ("catalog", "Validado por catálogo/fabricante"),
            ("lab", "Validado en laboratorio"),
            ("production", "Validado en producción"),
        ],
        string="Estado de validación",
        default="unverified",
        required=True,
    )
    alternate_languages = fields.Char(
        string="Lenguajes alternos",
        help=(
            "Códigos separados por coma. Ejemplo: zpl,epl. Direct Print los usa para "
            "negociar un renderer disponible sin cambiar el diseño de la etiqueta."
        ),
    )
    source_reference = fields.Char(
        string="Referencia técnica",
        help="URL, manual o referencia de fabricante usada para validar el perfil.",
    )
    notes = fields.Text(string="Notas de compatibilidad")

    def matches_printer_name(self, value):
        self.ensure_one()
        if not self.name_pattern or not value:
            return False
        try:
            return bool(re.search(self.name_pattern, value, flags=re.IGNORECASE))
        except re.error:
            # Un patrón capturado incorrectamente nunca debe impedir sincronizar impresoras.
            return False

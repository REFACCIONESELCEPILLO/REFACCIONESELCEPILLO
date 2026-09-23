# -*- coding: utf-8 -*-
"""Central print engine for ICKAB Direct Print.

The engine owns *how* a document is printed.  Functional modules only provide
content:

* regular Odoo reports provide PDF/text through ``ir.actions.report``;
* Label Studio provides a physical label design;
* fixed label modules (for example Auto Part Vehicle Labels) provide the same
  common internal label structure;
* future POS/carrier integrations can enqueue an already-rendered payload.

No UI/application is introduced by this file.  It is an internal service of the
single ``ickab_direct_print`` module.
"""

import base64
import io
import re

from odoo import _, api, models
from odoo.exceptions import UserError


LABEL_DOCUMENT_SCHEMA = "ickab.label.document/1"
PRINT_SOURCE_SCHEMA = "ickab.print.source/1"

# Native label renderers that currently live inside Direct Print.  Printers
# using any other language are still printable through the universal PDF/OS
# driver fallback whenever the host exposes a system printer queue.
NATIVE_LABEL_RENDERERS = ("zpl", "tspl")

# Payloads that are already printer-language byte streams.  The Agent transports
# them RAW and never interprets/re-renders them.
NATIVE_RAW_PAYLOAD_TYPES = {
    "zpl", "tspl", "epl", "cpcl", "escpos", "starprnt", "sbpl", "dpl",
    "ipl", "fingerprint", "brother_raster", "pcl", "postscript", "pwg_raster",
    "raw",
}

LANGUAGE_ALIASES = {
    "zpl2": "zpl",
    "zplii": "zpl",
    "tspl2": "tspl",
    "tsplii": "tspl",
    "epl2": "epl",
    "eplii": "epl",
    "escpos": "escpos",
    "esc/pos": "escpos",
    "star": "starprnt",
    "starprnt": "starprnt",
    "postscript": "postscript",
    "ps": "postscript",
    "pcl5": "pcl",
    "pcl6": "pcl",
    "pdf": "pdf",
    "driver": "pdf",
    "raster": "image",
}


class IckabPrintEngine(models.AbstractModel):
    _name = "ickab.print.engine"
    _description = "ICKAB Direct Print Engine"

    # ------------------------------------------------------------------
    # Public contract used by Direct Print integrations
    # ------------------------------------------------------------------

    @api.model
    def render_label_source(self, source, *, printer, paper=None):
        """Render a label design for the selected physical printer.

        ``source`` is intentionally independent from Label Studio.  Any module
        can emit the documented contract and obtain identical printer routing.
        """
        if not printer:
            raise UserError(_("Debe indicar una impresora para renderizar etiquetas."))
        source = source or {}
        if source.get("schema") != PRINT_SOURCE_SCHEMA or source.get("kind") != "label":
            raise UserError(_("La fuente de impresión de etiqueta no cumple el contrato ICKAB."))
        documents = source.get("documents") or []
        if not isinstance(documents, list) or not documents:
            raise UserError(_("No hay etiquetas para imprimir."))

        documents = [self._normalize_label_document(document) for document in documents]
        self._validate_common_media(documents, paper=paper)

        # RAW design (for example an imported untouched ZPL file) cannot be
        # translated safely.  It is accepted only by a compatible printer.
        raw_documents = [document for document in documents if document.get("mode") == "raw"]
        if raw_documents:
            if len(raw_documents) != len(documents):
                raise UserError(_("No se pueden mezclar etiquetas RAW con diseños editables en el mismo trabajo."))
            raw_language = self._normalize_language(raw_documents[0].get("raw_language"))
            if not raw_language:
                raise UserError(_("La etiqueta RAW no indica su lenguaje de impresora."))
            for document in raw_documents:
                if self._normalize_language(document.get("raw_language")) != raw_language:
                    raise UserError(_("No se pueden mezclar varios lenguajes RAW en un mismo trabajo."))
            self._assert_native_payload_compatible(printer, raw_language)
            content = []
            for document in raw_documents:
                copies = max(1, int(document.get("copies") or 1))
                raw_content = document.get("raw_content") or ""
                if isinstance(raw_content, bytes):
                    raw_content = raw_content.decode("utf-8", errors="strict")
                content.extend([str(raw_content).rstrip() + "\n"] * copies)
            return {
                "payload_type": raw_language,
                "payload": "".join(content),
                "mime_type": self._payload_mime_type(raw_language),
                "extension": self._payload_extension(raw_language),
                "renderer": "raw_passthrough",
                "dpi": self._target_dpi(printer, paper, documents[0].get("media")),
            }

        renderer = self._select_label_renderer(printer)
        dpi = self._target_dpi(printer, paper, documents[0].get("media"))
        if renderer == "zpl":
            payload = self._render_zpl(documents, printer=printer, paper=paper, dpi=dpi)
            return {
                "payload_type": "zpl",
                "payload": payload,
                "mime_type": "application/octet-stream",
                "extension": "zpl",
                "renderer": "zpl",
                "dpi": dpi,
            }
        if renderer == "tspl":
            payload = self._render_tspl(documents, printer=printer, paper=paper, dpi=dpi)
            return {
                "payload_type": "tspl",
                "payload": payload,
                "mime_type": "application/octet-stream",
                "extension": "tspl",
                "renderer": "tspl",
                "dpi": dpi,
            }

        # Universal fallback: create a correctly sized PDF and let the OS
        # printer driver perform the device-specific conversion.  This is what
        # keeps Label Studio/fixed labels independent from EPL/SBPL/DPL/etc.
        payload = self._render_pdf(documents)
        return {
            "payload_type": "pdf",
            "payload": payload,
            "mime_type": "application/pdf",
            "extension": "pdf",
            "renderer": "driver_pdf",
            "dpi": dpi,
        }

    @api.model
    def enqueue_payload(
        self,
        *,
        document_kind,
        payload_type,
        payload,
        printer=None,
        paper=None,
        copies=1,
        branch=None,
        source_record=None,
        report=None,
        filename=None,
        mime_type=None,
        user=None,
        company=None,
    ):
        """Generic Direct Print entry point for POS/carriers/future integrations.

        The caller owns the content.  Direct Print owns target resolution,
        validation, queueing and Agent delivery.
        """
        user = user or self.env.user
        company = company or self.env.company
        if document_kind not in {"label", "ticket", "document"}:
            raise UserError(_("Tipo de documento de impresión no válido: %s", document_kind))
        branch = branch or user._ickab_resolve_print_branch(company)

        if not printer:
            assignment = self.env["ickab.print.assignment"].resolve_assignment(
                document_kind, user=user, company=company, branch=branch
            )
            if assignment:
                printer = assignment.printer_id
                paper = paper or assignment.paper_id or printer.default_paper_id
                copies = int(copies or assignment.copies or 1)
        if not printer and branch:
            printer = branch.default_printer_for(document_kind)
        if not printer:
            raise UserError(_("No existe una impresora configurada para %s.", document_kind))
        if not paper:
            paper = printer.default_paper_id or (branch.default_paper_for(document_kind) if branch else False)

        return self.env["ickab.print.job"].enqueue(
            printer=printer,
            payload_type=payload_type,
            payload=payload,
            paper=paper,
            copies=max(1, int(copies or 1)),
            source_record=source_record,
            report=report,
            filename=filename,
            mime_type=mime_type,
            branch=branch,
        )

    # ------------------------------------------------------------------
    # Printer capability negotiation
    # ------------------------------------------------------------------

    @api.model
    def _normalize_language(self, value):
        value = str(value or "").strip().lower()
        compact = re.sub(r"[\s._-]+", "", value)
        return LANGUAGE_ALIASES.get(value) or LANGUAGE_ALIASES.get(compact) or value

    @api.model
    def _parse_languages(self, value):
        if not value:
            return []
        if isinstance(value, (list, tuple, set)):
            parts = list(value)
        else:
            parts = re.split(r"[,;/|\n]+", str(value))
        result = []
        for part in parts:
            language = self._normalize_language(part)
            if language and language not in result:
                result.append(language)
        return result

    @api.model
    def printer_supported_languages(self, printer):
        printer.ensure_one()
        result = []
        sources = [
            printer.language,
            getattr(printer, "alternate_languages", False),
        ]
        profile = printer.compatibility_profile_id
        if profile:
            sources.extend([profile.language, profile.alternate_languages])
        for source in sources:
            for language in self._parse_languages(source):
                if language not in result:
                    result.append(language)
        return result or ["raw"]

    @api.model
    def _select_label_renderer(self, printer):
        supported = self.printer_supported_languages(printer)
        preferred = self._normalize_language(printer.language)
        if preferred in NATIVE_LABEL_RENDERERS:
            return preferred
        for language in NATIVE_LABEL_RENDERERS:
            if language in supported:
                return language

        if self._driver_fallback_available(printer):
            return "pdf"
        raise UserError(_(
            "La impresora %(printer)s no tiene un renderer nativo disponible en Direct Print "
            "(%(languages)s) y tampoco dispone de una cola/driver para usar el fallback PDF. "
            "Configure la impresora mediante su driver del sistema operativo o añada soporte "
            "nativo dentro de ICKAB Direct Print.",
            printer=printer.display_name,
            languages=", ".join(code.upper() for code in supported),
        ))

    @api.model
    def _driver_fallback_available(self, printer):
        # On Windows a discovered/system queue is enough even when the preferred
        # transport for native labels is configured as windows_raw.  Agent 1.4+
        # switches to the driver automatically for PDF/image payloads.
        if printer.host_id.platform_type == "windows" and printer.system_name:
            return True
        if printer.transport in {"windows_spooler", "cups", "android_print_service"}:
            return True
        if printer.language in {"pdf", "image"}:
            return True
        return False

    @api.model
    def _assert_native_payload_compatible(self, printer, payload_type):
        payload_type = self._normalize_language(payload_type)
        if printer.language == "raw":
            return True
        supported = self.printer_supported_languages(printer)
        if payload_type not in supported:
            raise UserError(_(
                "La impresora %(printer)s no declara soporte para %(payload)s. "
                "Lenguajes configurados: %(supported)s.",
                printer=printer.display_name,
                payload=payload_type.upper(),
                supported=", ".join(code.upper() for code in supported),
            ))
        return True

    # ------------------------------------------------------------------
    # Internal label design validation
    # ------------------------------------------------------------------

    @api.model
    def _normalize_label_document(self, document):
        if not isinstance(document, dict) or document.get("schema") != LABEL_DOCUMENT_SCHEMA:
            raise UserError(_("El diseño de etiqueta recibido no cumple la estructura interna esperada."))
        media = document.get("media") or {}
        width = float(media.get("width_mm") or 0.0)
        height = float(media.get("height_mm") or 0.0)
        if width <= 0 or height <= 0:
            raise UserError(_("La etiqueta debe indicar ancho y alto físicos mayores a cero."))
        if document.get("mode") not in {"studio", "fixed", "raw"}:
            raise UserError(_("Modo de etiqueta no soportado: %s", document.get("mode")))
        if document.get("mode") != "raw" and not isinstance(document.get("elements") or [], list):
            raise UserError(_("La etiqueta no contiene una lista válida de elementos."))
        result = dict(document)
        result["media"] = dict(media)
        result["copies"] = max(1, int(result.get("copies") or 1))
        return result

    @api.model
    def _validate_common_media(self, documents, paper=None):
        first = documents[0].get("media") or {}
        width = float(first.get("width_mm") or 0.0)
        height = float(first.get("height_mm") or 0.0)
        for document in documents[1:]:
            media = document.get("media") or {}
            if abs(float(media.get("width_mm") or 0.0) - width) > 0.02 or abs(float(media.get("height_mm") or 0.0) - height) > 0.02:
                raise UserError(_("Un mismo trabajo no puede mezclar tamaños físicos de etiqueta."))
        if paper:
            if abs(float(paper.width_mm or 0.0) - width) > 0.05 or abs(float(paper.height_mm or 0.0) - height) > 0.05:
                raise UserError(_(
                    "El diseño mide %(dw).2f × %(dh).2f mm y el papel seleccionado %(pw).2f × %(ph).2f mm.",
                    dw=width, dh=height, pw=paper.width_mm, ph=paper.height_mm,
                ))

    @api.model
    def _target_dpi(self, printer, paper=None, media=None):
        if printer.dpi in ("203", "300", "600"):
            return int(printer.dpi)
        if paper and paper.default_dpi in ("203", "300", "600"):
            return int(paper.default_dpi)
        reference = int((media or {}).get("dpi_reference") or (media or {}).get("dpi") or 203)
        return reference if reference in (203, 300, 600) else 203

    # ------------------------------------------------------------------
    # ZPL renderer
    # ------------------------------------------------------------------

    @staticmethod
    def _zpl_escape(value, preserve_newlines=False):
        text = str(value or "").replace("\r\n", "\n").replace("\r", "\n")

        def one(line):
            return (
                line.replace("_", "_5F")
                .replace("\\", "_5C")
                .replace("^", "_5E")
                .replace("~", "_7E")
            )

        if preserve_newlines:
            return "\\&".join(one(line) for line in text.split("\n"))
        return one(re.sub(r"\s+", " ", text).strip())

    @api.model
    def _render_zpl(self, documents, *, printer, paper, dpi):
        chunks = []
        for document in documents:
            media = document["media"]
            width_mm = float(media["width_mm"])
            height_mm = float(media["height_mm"])
            dot = lambda mm: max(0, int(round(float(mm or 0.0) * dpi / 25.4)))
            if hasattr(printer, "_ickab_zpl_preamble"):
                lines = [printer._ickab_zpl_preamble(width_mm, height_mm, dpi=dpi).rstrip()]
            else:
                lines = [
                    "^XA", "^CI28", f"^PW{dot(width_mm)}", f"^LL{dot(height_mm)}",
                    "^LH0,0", "^LT0", "^LS0",
                ]
            for element in sorted(document.get("elements") or [], key=lambda item: (int(item.get("z", 0) or 0), str(item.get("id") or ""))):
                etype = element.get("type")
                x = dot(element.get("x_mm"))
                y = dot(element.get("y_mm"))
                w = max(1, dot(element.get("w_mm")))
                h = max(1, dot(element.get("h_mm")))
                value = element.get("value") or ""
                if etype == "text":
                    escaped = self._zpl_escape(value, preserve_newlines=True)
                    font_dot = max(4, dot(element.get("font_mm") or 3.0))
                    align = element.get("align") if element.get("align") in {"L", "C", "R", "J"} else "L"
                    max_lines = max(1, int(element.get("max_lines") or 1))
                    lines.extend([
                        f"^FO{x},{y}", f"^A0N,{font_dot},{font_dot}",
                        f"^FB{w},{max_lines},0,{align},0", "^FH_", f"^FD{escaped}^FS",
                    ])
                elif etype == "barcode" and value:
                    kind = str(element.get("barcode_type") or "code128").lower()
                    escaped = self._zpl_escape(value)
                    human = "Y" if element.get("human_readable", True) else "N"
                    modules_estimate = max(35, len(str(value)) * (11 if kind == "code128" else 14) + 24)
                    module_width = max(1, min(10, int(w / modules_estimate)))
                    lines.extend([f"^FO{x},{y}", f"^BY{module_width},2,{max(10, h)}"])
                    if kind == "code39":
                        lines.append(f"^B3N,N,{max(10, h)},{human},N")
                    elif kind == "ean13":
                        lines.append(f"^BEN,{max(10, h)},{human},N")
                    elif kind == "upca":
                        lines.append(f"^BUN,{max(10, h)},{human},N")
                    else:
                        lines.append(f"^BCN,{max(10, h)},{human},N,N")
                    lines.extend(["^FH_", f"^FD{escaped}^FS"])
                elif etype == "qrcode" and value:
                    magnification = max(1, min(10, int(element.get("magnification") or 4)))
                    lines.extend([
                        f"^FO{x},{y}", f"^BQN,2,{magnification}", "^FH_",
                        f"^FDLA,{self._zpl_escape(value)}^FS",
                    ])
                elif etype == "box":
                    thickness = max(1, dot(element.get("thickness_mm") or 0.25))
                    rounding = max(0, min(8, int(element.get("rounding") or 0)))
                    lines.append(f"^FO{x},{y}^GB{w},{h},{thickness},B,{rounding}^FS")
                elif etype == "line":
                    thickness = max(1, dot(element.get("thickness_mm") or 0.25))
                    if element.get("line_direction") == "vertical":
                        line_x = x + max(0, (w - thickness) // 2)
                        lines.append(f"^FO{line_x},{y}^GB{thickness},{h},{thickness},B,0^FS")
                    else:
                        line_y = y + max(0, (h - thickness) // 2)
                        lines.append(f"^FO{x},{line_y}^GB{w},{thickness},{thickness},B,0^FS")
                elif etype == "image":
                    bitmap, bytes_per_row = self._element_mono_bitmap(element, w, h)
                    if bitmap:
                        total = len(bitmap)
                        lines.extend([
                            f"^FO{x},{y}",
                            f"^GFA,{total},{total},{bytes_per_row},{bitmap.hex().upper()}",
                            "^FS",
                        ])
            lines.append(f"^PQ{max(1, int(document.get('copies') or 1))},0,1,N")
            lines.append("^XZ")
            chunks.append("\n".join(lines) + "\n")
        return "".join(chunks)

    # ------------------------------------------------------------------
    # TSPL renderer
    # ------------------------------------------------------------------

    @staticmethod
    def _tspl_quote(value):
        text = str(value or "").replace("\r", " ").replace("\n", " ")
        return text.replace('"', "'")

    @api.model
    def _tspl_font(self, font_mm, dpi):
        # Resident TSPL fonts have fixed pixel cells.  Pick the closest readable
        # height while keeping the design's geometry in millimetres.
        target = max(1, int(round(float(font_mm or 2.0) * dpi / 25.4)))
        fonts = [("1", 12), ("2", 20), ("3", 24), ("4", 32), ("5", 48)]
        return min(fonts, key=lambda item: abs(item[1] - target))[0]

    @api.model
    def _render_tspl(self, documents, *, printer, paper, dpi):
        chunks = bytearray()
        profile = printer.compatibility_profile_id
        bitmap_one_is_black = bool(profile.tspl_bitmap_one_is_black) if profile else True
        for document in documents:
            media = document["media"]
            width_mm = float(media["width_mm"])
            height_mm = float(media["height_mm"])
            dot = lambda mm: max(0, int(round(float(mm or 0.0) * dpi / 25.4)))
            if hasattr(printer, "_ickab_tspl_preamble"):
                preamble = printer._ickab_tspl_preamble(width_mm, height_mm, paper=paper)
            else:
                gap = float(media.get("gap_mm") or 0.0)
                offset = float(media.get("gap_offset_mm") or 0.0)
                preamble = f"SIZE {width_mm:g} mm,{height_mm:g} mm\r\nGAP {gap:g} mm,{offset:g} mm\r\nDIRECTION 1\r\nREFERENCE 0,0\r\nCODEPAGE 850\r\n"
            chunks.extend(preamble.encode("ascii", errors="replace"))
            chunks.extend(b"CLS\r\n")
            for element in sorted(document.get("elements") or [], key=lambda item: (int(item.get("z", 0) or 0), str(item.get("id") or ""))):
                etype = element.get("type")
                x = dot(element.get("x_mm"))
                y = dot(element.get("y_mm"))
                w = max(1, dot(element.get("w_mm")))
                h = max(1, dot(element.get("h_mm")))
                value = self._tspl_quote(element.get("value") or "")
                if etype == "text":
                    font = self._tspl_font(element.get("font_mm") or 2.0, dpi)
                    chunks.extend(f'TEXT {x},{y},"{font}",0,1,1,"{value}"\r\n'.encode("cp850", errors="replace"))
                elif etype == "barcode" and value:
                    human = 2 if element.get("human_readable", True) else 0
                    kind = str(element.get("barcode_type") or "code128").lower()
                    code = {"code39": "39", "ean13": "EAN13", "upca": "UPCA"}.get(kind, "128")
                    narrow = max(1, min(5, int(round(w / max(45, len(value) * 11)))))
                    wide = max(narrow + 1, narrow * 2)
                    command = f'BARCODE {x},{y},"{code}",{max(8, h)},{human},0,{narrow},{wide},"{value}"\r\n'
                    chunks.extend(command.encode("cp850", errors="replace"))
                elif etype == "qrcode" and value:
                    cell = max(1, min(10, int(element.get("magnification") or 4)))
                    chunks.extend(f'QRCODE {x},{y},L,{cell},A,0,M2,S7,"{value}"\r\n'.encode("cp850", errors="replace"))
                elif etype == "box":
                    thickness = max(1, dot(element.get("thickness_mm") or 0.25))
                    chunks.extend(f"BOX {x},{y},{x+w},{y+h},{thickness}\r\n".encode("ascii"))
                elif etype == "line":
                    thickness = max(1, dot(element.get("thickness_mm") or 0.25))
                    if element.get("line_direction") == "vertical":
                        line_x = x + max(0, (w - thickness) // 2)
                        chunks.extend(f"BAR {line_x},{y},{thickness},{h}\r\n".encode("ascii"))
                    else:
                        line_y = y + max(0, (h - thickness) // 2)
                        chunks.extend(f"BAR {x},{line_y},{w},{thickness}\r\n".encode("ascii"))
                elif etype == "image":
                    bitmap, bytes_per_row = self._element_mono_bitmap(element, w, h)
                    if bitmap:
                        if not bitmap_one_is_black:
                            bitmap = bytes(byte ^ 0xFF for byte in bitmap)
                        chunks.extend(f"BITMAP {x},{y},{bytes_per_row},{h},0,".encode("ascii"))
                        chunks.extend(bitmap)
                        chunks.extend(b"\r\n")
            copies = max(1, int(document.get("copies") or 1))
            chunks.extend(f"PRINT {copies},1\r\n".encode("ascii"))
        return bytes(chunks)

    # ------------------------------------------------------------------
    # Universal PDF/driver renderer
    # ------------------------------------------------------------------

    @api.model
    def _render_pdf(self, documents):
        try:
            from reportlab.graphics import renderPDF
            from reportlab.graphics.barcode import createBarcodeDrawing
            from reportlab.lib.utils import ImageReader
            from reportlab.pdfgen import canvas
        except Exception as exc:  # pragma: no cover - standard Odoo dependency
            raise UserError(_("ReportLab no está disponible para el fallback universal de impresión.")) from exc

        buffer = io.BytesIO()
        pdf = None
        mm_pt = 72.0 / 25.4

        for document in documents:
            media = document["media"]
            width_pt = float(media["width_mm"]) * mm_pt
            height_pt = float(media["height_mm"]) * mm_pt
            copies = max(1, int(document.get("copies") or 1))
            for _copy in range(copies):
                if pdf is None:
                    pdf = canvas.Canvas(buffer, pagesize=(width_pt, height_pt), pageCompression=1)
                else:
                    pdf.setPageSize((width_pt, height_pt))
                for element in sorted(document.get("elements") or [], key=lambda item: (int(item.get("z", 0) or 0), str(item.get("id") or ""))):
                    etype = element.get("type")
                    x = float(element.get("x_mm") or 0.0) * mm_pt
                    y_top = float(element.get("y_mm") or 0.0) * mm_pt
                    w = max(0.1, float(element.get("w_mm") or 0.1) * mm_pt)
                    h = max(0.1, float(element.get("h_mm") or 0.1) * mm_pt)
                    y = height_pt - y_top - h
                    value = str(element.get("value") or "")
                    if etype == "text":
                        font_size = max(3.0, float(element.get("font_mm") or 3.0) * mm_pt)
                        pdf.setFont("Helvetica", font_size)
                        lines = value.replace("\r\n", "\n").replace("\r", "\n").split("\n")
                        max_lines = max(1, int(element.get("max_lines") or len(lines) or 1))
                        lines = lines[:max_lines]
                        leading = font_size * 1.12
                        align = element.get("align") or "L"
                        for index, line in enumerate(lines):
                            baseline = y + h - font_size - index * leading
                            if baseline < y:
                                break
                            if align == "C":
                                pdf.drawCentredString(x + w / 2.0, baseline, line)
                            elif align == "R":
                                pdf.drawRightString(x + w, baseline, line)
                            else:
                                pdf.drawString(x, baseline, line)
                    elif etype in {"barcode", "qrcode"} and value:
                        kind = str(element.get("barcode_type") or "code128").lower()
                        barcode_type = "QR" if etype == "qrcode" else {
                            "code39": "Standard39", "ean13": "EAN13", "upca": "UPCA"
                        }.get(kind, "Code128")
                        options = {"value": value, "humanReadable": bool(element.get("human_readable", True))}
                        if etype == "qrcode":
                            options = {"value": value}
                        try:
                            drawing = createBarcodeDrawing(barcode_type, **options)
                            sx = w / max(1.0, float(drawing.width))
                            sy = h / max(1.0, float(drawing.height))
                            scale = min(sx, sy)
                            pdf.saveState()
                            pdf.translate(x + (w - drawing.width * scale) / 2.0, y + (h - drawing.height * scale) / 2.0)
                            pdf.scale(scale, scale)
                            renderPDF.draw(drawing, pdf, 0, 0)
                            pdf.restoreState()
                        except Exception as exc:
                            raise UserError(_("No fue posible renderizar el código '%s' en PDF.") % value) from exc
                    elif etype == "box":
                        thickness = max(0.2, float(element.get("thickness_mm") or 0.25) * mm_pt)
                        pdf.setLineWidth(thickness)
                        pdf.rect(x, y, w, h, stroke=1, fill=0)
                    elif etype == "line":
                        thickness = max(0.2, float(element.get("thickness_mm") or 0.25) * mm_pt)
                        pdf.setLineWidth(thickness)
                        if element.get("line_direction") == "vertical":
                            cx = x + w / 2.0
                            pdf.line(cx, y, cx, y + h)
                        else:
                            cy = y + h / 2.0
                            pdf.line(x, cy, x + w, cy)
                    elif etype == "image":
                        raw = self._element_image_bytes(element)
                        if raw:
                            try:
                                reader = ImageReader(io.BytesIO(raw))
                                image_w, image_h = reader.getSize()
                                scale = min(w / max(1.0, float(image_w)), h / max(1.0, float(image_h)))
                                draw_w = max(0.1, float(image_w) * scale)
                                draw_h = max(0.1, float(image_h) * scale)
                                draw_x = x + (w - draw_w) / 2.0
                                draw_y = y + (h - draw_h) / 2.0
                                pdf.drawImage(reader, draw_x, draw_y, width=draw_w, height=draw_h, mask="auto")
                            except Exception as exc:
                                raise UserError(_("No fue posible renderizar una imagen de la etiqueta en PDF.")) from exc
                pdf.showPage()
        if pdf is None:
            raise UserError(_("No hay páginas de etiqueta para generar."))
        pdf.save()
        return buffer.getvalue()

    # ------------------------------------------------------------------
    # Image helpers shared by native renderers
    # ------------------------------------------------------------------

    @api.model
    def _element_image_bytes(self, element):
        encoded = element.get("image_source_b64") or ""
        if not encoded:
            return b""
        try:
            return base64.b64decode(encoded, validate=True)
        except Exception as exc:
            raise UserError(_("La imagen de la etiqueta no contiene Base64 válido.")) from exc

    @api.model
    def _element_mono_bitmap(self, element, width_dot, height_dot):
        raw = self._element_image_bytes(element)
        if not raw:
            # Backward compatibility with documents generated by older Studio
            # releases that already contained a 1-bit bitmap.
            encoded = element.get("image_bitmap_b64") or ""
            if not encoded:
                return b"", 0
            try:
                bitmap = base64.b64decode(encoded)
            except Exception as exc:
                raise UserError(_("La imagen térmica no contiene un bitmap válido.")) from exc
            return bitmap, int(element.get("image_bytes_per_row") or ((width_dot + 7) // 8))

        try:
            from PIL import Image, ImageOps
        except Exception as exc:  # pragma: no cover - standard Odoo dependency
            raise UserError(_("Pillow no está disponible para procesar imágenes de etiqueta.")) from exc
        try:
            image = Image.open(io.BytesIO(raw))
            image.load()
            image = ImageOps.exif_transpose(image).convert("RGBA")
        except Exception as exc:
            raise UserError(_("No fue posible abrir una imagen del diseño de etiqueta.")) from exc

        width_dot = max(1, int(width_dot or 1))
        height_dot = max(1, int(height_dot or 1))
        target = (width_dot, height_dot)
        resampling = getattr(Image, "Resampling", Image).LANCZOS
        fit = str(element.get("fit") or "contain")
        if fit == "stretch":
            canvas = image.resize(target, resampling)
        elif fit == "cover":
            canvas = ImageOps.fit(image, target, method=resampling, centering=(0.5, 0.5))
        else:
            fitted = ImageOps.contain(image, target, method=resampling)
            canvas = Image.new("RGBA", target, (255, 255, 255, 255))
            canvas.alpha_composite(fitted, ((width_dot - fitted.width) // 2, (height_dot - fitted.height) // 2))
        background = Image.new("RGBA", target, (255, 255, 255, 255))
        background.alpha_composite(canvas)
        gray = background.convert("RGB").convert("L")
        if bool(element.get("invert")):
            gray = ImageOps.invert(gray)
        threshold = max(0, min(255, int(element.get("threshold", 128) or 128)))
        dither = str(element.get("dither") or "none")
        if dither == "floyd_steinberg":
            mode = Image.Dither.FLOYDSTEINBERG if hasattr(Image, "Dither") else Image.FLOYDSTEINBERG
            mono = gray.convert("1", dither=mode)
        else:
            mono = gray.point(lambda pixel: 0 if pixel <= threshold else 255, mode="1")

        bytes_per_row = (width_dot + 7) // 8
        packed = bytearray(bytes_per_row * height_dot)
        pixels = mono.load()
        for y in range(height_dot):
            offset = y * bytes_per_row
            for x in range(width_dot):
                if pixels[x, y] == 0:
                    packed[offset + (x // 8)] |= 0x80 >> (x % 8)
        return bytes(packed), bytes_per_row

    # ------------------------------------------------------------------
    # Generic payload metadata
    # ------------------------------------------------------------------

    @api.model
    def _payload_extension(self, payload_type):
        return {
            "zpl": "zpl", "tspl": "tspl", "epl": "epl", "cpcl": "cpcl",
            "escpos": "bin", "starprnt": "bin", "sbpl": "sbpl", "dpl": "dpl",
            "ipl": "ipl", "fingerprint": "txt", "brother_raster": "bin",
            "pcl": "pcl", "postscript": "ps", "pwg_raster": "ras", "pdf": "pdf",
            "image": "png", "raw": "bin",
        }.get(payload_type, "bin")

    @api.model
    def _payload_mime_type(self, payload_type):
        return {
            "pdf": "application/pdf",
            "image": "image/png",
            "postscript": "application/postscript",
            "pcl": "application/octet-stream",
            "pwg_raster": "image/pwg-raster",
        }.get(payload_type, "application/octet-stream")

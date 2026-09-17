# Copyright 2026 ICKAB. All rights reserved.
import base64
import re

from odoo import _, models
from odoo.exceptions import UserError


class IckabLabelRendererZpl(models.AbstractModel):
    _name = "ickab.label.renderer.zpl"
    _description = "ICKAB Label Studio ZPL Renderer"

    @staticmethod
    def _escape_zpl(value, preserve_newlines=False):
        """Escape field data using ``^FH_`` without changing visible content.

        The underscore is also escaped so a literal ``_5E`` in business data can
        never be reinterpreted as a hexadecimal sequence by the printer.  Text
        elements preserve explicit line breaks through the native ``^FB`` ``\\&``
        sequence; barcode/QR values intentionally flatten control characters.
        """
        text = str(value or "").replace("\r\n", "\n").replace("\r", "\n")

        def escape_line(line):
            # Order matters: escape the ^FH indicator itself first.
            return (
                line.replace("_", "_5F")
                .replace("\\", "_5C")
                .replace("^", "_5E")
                .replace("~", "_7E")
            )

        if preserve_newlines:
            return "\\&".join(escape_line(line) for line in text.split("\n"))
        text = re.sub(r"[\n\t]+", " ", text)
        text = re.sub(r"\s+", " ", text).strip()
        return escape_line(text)

    @staticmethod
    def _validate_barcode(kind, raw_value):
        value = str(raw_value or "")
        if not value:
            return value
        if kind == "code128":
            if any(ord(char) < 32 or ord(char) > 126 for char in value):
                raise UserError(_("Code 128 sólo admite caracteres ASCII imprimibles en esta versión."))
        elif kind == "code39":
            if not re.fullmatch(r"[0-9A-Z .\-$/+%]+", value.upper()):
                raise UserError(_("El valor '%s' contiene caracteres no válidos para Code 39.", value))
            value = value.upper()
        elif kind == "ean13":
            if not (value.isdigit() and len(value) in (12, 13)):
                raise UserError(_("EAN-13 requiere 12 o 13 dígitos."))
        elif kind == "upca":
            if not (value.isdigit() and len(value) in (11, 12)):
                raise UserError(_("UPC-A requiere 11 o 12 dígitos."))
        return value

    def render(self, template, record=None, dpi=None, copies=1):
        template.ensure_one()
        target_dpi = int(dpi or template.dpi or 203)
        width_dots, height_dots = template._size_dots(dpi=target_dpi)
        copies = max(1, int(copies or 1))
        lines = [
            "^XA",
            "^CI28",
            f"^PW{width_dots}",
            f"^LL{height_dots}",
            "^LH0,0",
            "^LT0",
            "^LS0",
        ]

        for element in template.resolve_elements(record=record, dpi=target_dpi):
            etype = element["type"]
            x, y = element["x_dot"], element["y_dot"]
            w, h = element["w_dot"], element["h_dot"]
            raw_value = element.get("value_resolved", "")

            if etype == "text":
                value = self._escape_zpl(raw_value, preserve_newlines=True)
                font_mm = float(element.get("font_mm") or 3.0)
                font_dots = max(4, round(font_mm * target_dpi / 25.4))
                align = element.get("align", "L")
                max_lines = max(1, int(element.get("max_lines") or 1))
                lines.extend([
                    f"^FO{x},{y}",
                    f"^A0N,{font_dots},{font_dots}",
                    f"^FB{w},{max_lines},0,{align},0",
                    "^FH_",
                    f"^FD{value}^FS",
                ])
            elif etype == "barcode":
                if not raw_value:
                    continue
                kind = element.get("barcode_type", "code128")
                raw_value = self._validate_barcode(kind, raw_value)
                value = self._escape_zpl(raw_value)
                human = "Y" if element.get("human_readable", True) else "N"
                modules_estimate = max(35, len(raw_value) * (11 if kind == "code128" else 14) + 24)
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
                lines.extend(["^FH_", f"^FD{value}^FS"])
            elif etype == "qrcode":
                if not raw_value:
                    continue
                value = self._escape_zpl(raw_value)
                magnification = max(1, min(10, int(element.get("magnification") or 4)))
                lines.extend([f"^FO{x},{y}", f"^BQN,2,{magnification}", "^FH_", f"^FDLA,{value}^FS"])
            elif etype == "box":
                thickness = max(1, round(float(element.get("thickness_mm") or 0.25) * target_dpi / 25.4))
                rounding = max(0, min(8, int(element.get("rounding") or 0)))
                lines.append(f"^FO{x},{y}^GB{w},{h},{thickness},B,{rounding}^FS")
            elif etype == "line":
                thickness = max(1, round(float(element.get("thickness_mm") or 0.25) * target_dpi / 25.4))
                # Canvas and HTML preview draw lines in the centre of the element's
                # physical bounding box.  ZPL must use the same geometry.
                if element.get("line_direction") == "vertical":
                    line_x = x + max(0, (w - thickness) // 2)
                    lines.append(f"^FO{line_x},{y}^GB{thickness},{h},{thickness},B,0^FS")
                else:
                    line_y = y + max(0, (h - thickness) // 2)
                    lines.append(f"^FO{x},{line_y}^GB{w},{thickness},{thickness},B,0^FS")
            elif etype == "image":
                encoded = element.get("image_bitmap_b64") or ""
                if not encoded:
                    continue
                try:
                    bitmap = base64.b64decode(encoded)
                except Exception as exc:
                    raise UserError(_("La imagen de la etiqueta no contiene un bitmap válido.")) from exc
                bytes_per_row = int(element.get("image_bytes_per_row") or ((w + 7) // 8))
                if bytes_per_row <= 0 or not bitmap:
                    continue
                total_bytes = len(bitmap)
                graphic_hex = bitmap.hex().upper()
                lines.extend([
                    f"^FO{x},{y}",
                    f"^GFA,{total_bytes},{total_bytes},{bytes_per_row},{graphic_hex}",
                    "^FS",
                ])

        lines.append(f"^PQ{copies},0,1,N")
        lines.append("^XZ")
        return {
            "language": "zpl",
            "content": "\n".join(lines),
            "content_type": "application/octet-stream",
            "extension": "zpl",
            "dpi": target_dpi,
            "width_mm": template.width_mm,
            "height_mm": template.height_mm,
            "copies": copies,
        }

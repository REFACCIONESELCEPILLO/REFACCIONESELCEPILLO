# Copyright 2026 ICKAB. All rights reserved.
import re

from odoo import _, models
from odoo.exceptions import UserError


MAX_ZPL_BYTES = 2 * 1024 * 1024
MAX_ZPL_TOKENS = 20000
MAX_IMPORT_ELEMENTS = 500


class IckabLabelZplParser(models.AbstractModel):
    _name = "ickab.label.zpl.parser"
    _description = "ICKAB Label Studio ZPL Import Parser"

    # Harmless configuration/transport commands which do not alter object geometry.
    _IGNORED = {
        "^XA", "^XZ", "^CI", "^PR", "^MD", "^MM", "^MN", "^PQ",
        "^JM", "^MT", "^SS", "^SC", "^JUS", "^FX", "~SD",
    }
    # Commands we can partially preview but cannot round-trip with exact semantics.
    # Their presence forces automatic import into RAW mode.
    _LOSSY = {"^FT", "^CF", "^LT", "^LS", "^PO", "^PM"}
    _HANDLED = {
        "^PW", "^LL", "^LH", "^FO", "^A0", "^FB", "^BY", "^BC",
        "^B3", "^BE", "^BU", "^BQ", "^GB", "^FD", "^FS", "^FH",
    }
    _KNOWN = _IGNORED | _LOSSY | _HANDLED

    @staticmethod
    def _tokens(zpl):
        text = str(zpl or "")
        matches = list(re.finditer(r"([\^~][A-Za-z0-9@]{2})", text))
        if len(matches) > MAX_ZPL_TOKENS:
            raise UserError(_(
                "El ZPL contiene más de %(max)s comandos y excede el límite seguro de importación.",
                max=MAX_ZPL_TOKENS,
            ))
        result = []
        for index, match in enumerate(matches):
            end = matches[index + 1].start() if index + 1 < len(matches) else len(text)
            result.append((match.group(1).upper(), text[match.end():end]))
        return result

    @staticmethod
    def _numbers(params, count=None):
        values = []
        for part in str(params or "").split(","):
            part = part.strip()
            if part == "":
                values.append(None)
                continue
            try:
                values.append(float(part))
            except ValueError:
                values.append(None)
        if count:
            values += [None] * max(0, count - len(values))
            return values[:count]
        return values

    @staticmethod
    def _dot_to_mm(value, dpi):
        return round(float(value or 0) * 25.4 / float(dpi), 3)

    @staticmethod
    def _clean_fd(value, hex_indicator=None):
        value = str(value or "")
        if value.startswith("LA,"):
            value = value[3:]
        if hex_indicator:
            indicator = re.escape(hex_indicator)

            def decode(match):
                try:
                    return bytes([int(match.group(1), 16)]).decode("latin-1")
                except Exception:
                    return match.group(0)

            value = re.sub(indicator + r"([0-9A-Fa-f]{2})", decode, value)
        return value.replace("\\&", "\n").strip()

    def parse(self, zpl, dpi=203):
        text = str(zpl or "")
        if len(text.encode("utf-8")) > MAX_ZPL_BYTES:
            raise UserError(_("El archivo ZPL excede el límite seguro de 2 MB."))
        dpi = int(dpi or 203)
        if dpi not in (203, 300, 600):
            dpi = 203
        tokens = self._tokens(text)
        unsupported = []
        for command, _params in tokens:
            if command not in self._KNOWN or command in self._LOSSY:
                if command not in unsupported:
                    unsupported.append(command)

        width_dots = 0
        height_dots = 0
        origin_x = origin_y = 0.0
        label_top = 0.0
        label_shift = 0.0
        cursor_x = cursor_y = 0.0
        cursor_is_baseline = False
        font_height = 30.0
        font_width = 30.0
        block_width = None
        block_lines = 1
        block_align = "L"
        by_module = 2.0
        by_height = 80.0
        current_kind = "text"
        current_barcode = None
        current_barcode_height = None
        current_human = True
        current_qr_mag = 4
        pending_fd = None
        hex_indicator = None
        elements = []
        sequence = 0
        visual_count = 0
        preview_truncated = False

        def add_element(element):
            nonlocal sequence, visual_count, preview_truncated
            visual_count += 1
            if len(elements) >= MAX_IMPORT_ELEMENTS:
                preview_truncated = True
                return
            sequence += 1
            element.setdefault("id", f"zpl_{sequence:04d}")
            element.setdefault("z", sequence)
            elements.append(element)

        def object_xy():
            x = cursor_x + origin_x + label_shift
            y = cursor_y + origin_y + label_top
            if cursor_is_baseline:
                y = max(0, y - font_height)
            return x, y

        def commit_field():
            nonlocal pending_fd, current_kind, current_barcode, block_width
            nonlocal block_lines, block_align, hex_indicator
            if pending_fd is None:
                current_kind = "text"
                current_barcode = None
                return
            value = self._clean_fd(pending_fd, hex_indicator=hex_indicator)
            x, y = object_xy()
            if current_kind == "barcode":
                height = current_barcode_height or by_height or 80
                estimated_modules = max(35, len(value) * (11 if current_barcode == "code128" else 14) + 24)
                width = estimated_modules * max(1, by_module)
                add_element({
                    "type": "barcode",
                    "x_mm": self._dot_to_mm(x, dpi), "y_mm": self._dot_to_mm(y, dpi),
                    "w_mm": self._dot_to_mm(width, dpi), "h_mm": self._dot_to_mm(height, dpi),
                    "source": "static", "value": value, "sample": "", "field_path": "",
                    "barcode_type": current_barcode or "code128",
                    "human_readable": bool(current_human),
                })
            elif current_kind == "qrcode":
                size = max(21, 29) * max(1, int(current_qr_mag or 4))
                add_element({
                    "type": "qrcode",
                    "x_mm": self._dot_to_mm(x, dpi), "y_mm": self._dot_to_mm(y, dpi),
                    "w_mm": self._dot_to_mm(size, dpi), "h_mm": self._dot_to_mm(size, dpi),
                    "source": "static", "value": value, "sample": "", "field_path": "",
                    "magnification": max(1, min(10, int(current_qr_mag or 4))),
                })
            else:
                width = block_width or max(font_width * max(1, max((len(line) for line in value.split("\n")), default=1)), font_width * 4)
                logical_lines = max(1, len(value.split("\n")), int(block_lines or 1))
                height = max(font_height, font_height * logical_lines)
                add_element({
                    "type": "text",
                    "x_mm": self._dot_to_mm(x, dpi), "y_mm": self._dot_to_mm(y, dpi),
                    "w_mm": self._dot_to_mm(width, dpi), "h_mm": self._dot_to_mm(height, dpi),
                    "source": "static", "value": value, "sample": "", "field_path": "",
                    "font_mm": max(0.5, self._dot_to_mm(font_height, dpi)),
                    "align": block_align if block_align in {"L", "C", "R", "J"} else "L",
                    "max_lines": logical_lines,
                })
            pending_fd = None
            current_kind = "text"
            current_barcode = None
            block_width = None
            block_lines = 1
            block_align = "L"
            hex_indicator = None

        for command, params in tokens:
            if command == "^PW":
                nums = self._numbers(params, 1)
                width_dots = int(nums[0] or width_dots or 0)
            elif command == "^LL":
                nums = self._numbers(params, 1)
                height_dots = int(nums[0] or height_dots or 0)
            elif command == "^LH":
                nums = self._numbers(params, 2)
                origin_x, origin_y = nums[0] or 0, nums[1] or 0
            elif command == "^LT":
                nums = self._numbers(params, 1)
                label_top = nums[0] or 0
            elif command == "^LS":
                nums = self._numbers(params, 1)
                label_shift = nums[0] or 0
            elif command in {"^FO", "^FT"}:
                nums = self._numbers(params, 2)
                cursor_x, cursor_y = nums[0] or 0, nums[1] or 0
                cursor_is_baseline = command == "^FT"
            elif command == "^A0":
                parts = str(params or "").split(",")
                if len(parts) > 1 and parts[1].strip():
                    try: font_height = float(parts[1])
                    except ValueError: pass
                if len(parts) > 2 and parts[2].strip():
                    try: font_width = float(parts[2])
                    except ValueError: pass
                else:
                    font_width = font_height
            elif command == "^CF":
                parts = str(params or "").split(",")
                if len(parts) > 1 and parts[1].strip():
                    try: font_height = float(parts[1])
                    except ValueError: pass
                if len(parts) > 2 and parts[2].strip():
                    try: font_width = float(parts[2])
                    except ValueError: pass
            elif command == "^FB":
                parts = str(params or "").split(",")
                try: block_width = float(parts[0]) if parts and parts[0].strip() else None
                except ValueError: block_width = None
                try: block_lines = int(float(parts[1])) if len(parts) > 1 and parts[1].strip() else 1
                except ValueError: block_lines = 1
                block_align = (parts[3].strip().upper() if len(parts) > 3 else "L") or "L"
            elif command == "^BY":
                nums = self._numbers(params, 3)
                by_module = nums[0] or by_module
                by_height = nums[2] or by_height
            elif command in {"^BC", "^B3", "^BE", "^BU"}:
                current_kind = "barcode"
                current_barcode = {"^BC": "code128", "^B3": "code39", "^BE": "ean13", "^BU": "upca"}[command]
                parts = str(params or "").split(",")
                height_index = 2 if command == "^B3" else 1
                human_index = 3 if command == "^B3" else 2
                try:
                    current_barcode_height = float(parts[height_index]) if len(parts) > height_index and parts[height_index].strip() else by_height
                except ValueError:
                    current_barcode_height = by_height
                human_part = parts[human_index].strip().upper() if len(parts) > human_index else "Y"
                current_human = human_part != "N"
            elif command == "^BQ":
                current_kind = "qrcode"
                parts = str(params or "").split(",")
                try: current_qr_mag = int(float(parts[2])) if len(parts) > 2 and parts[2].strip() else 4
                except ValueError: current_qr_mag = 4
            elif command == "^GB":
                nums = self._numbers(params, 5)
                gb_w, gb_h, thickness = nums[0] or 1, nums[1] or 1, nums[2] or 1
                rounding = int(nums[4] or 0) if nums[4] is not None else 0
                x, y = object_xy()
                vertical = gb_w <= max(2, thickness * 2) and gb_h > gb_w
                horizontal = gb_h <= max(2, thickness * 2) and gb_w > gb_h
                if vertical or horizontal:
                    add_element({
                        "type": "line", "x_mm": self._dot_to_mm(x, dpi), "y_mm": self._dot_to_mm(y, dpi),
                        "w_mm": self._dot_to_mm(max(gb_w, thickness), dpi),
                        "h_mm": self._dot_to_mm(max(gb_h, thickness), dpi),
                        "thickness_mm": max(0.1, self._dot_to_mm(thickness, dpi)),
                        "line_direction": "vertical" if vertical else "horizontal",
                    })
                else:
                    add_element({
                        "type": "box", "x_mm": self._dot_to_mm(x, dpi), "y_mm": self._dot_to_mm(y, dpi),
                        "w_mm": self._dot_to_mm(gb_w, dpi), "h_mm": self._dot_to_mm(gb_h, dpi),
                        "thickness_mm": max(0.1, self._dot_to_mm(thickness, dpi)),
                        "rounding": max(0, min(8, rounding)),
                    })
            elif command == "^FH":
                indicator = str(params or "").strip()
                hex_indicator = indicator[0] if indicator else "_"
            elif command == "^FD":
                pending_fd = params
            elif command == "^FS":
                commit_field()

        commit_field()

        if width_dots:
            width_mm = self._dot_to_mm(width_dots, dpi)
        else:
            max_x = max((el.get("x_mm", 0) + el.get("w_mm", 0) for el in elements), default=45)
            width_mm = max(50.0, max_x + 5)
        if height_dots:
            height_mm = self._dot_to_mm(height_dots, dpi)
        else:
            max_y = max((el.get("y_mm", 0) + el.get("h_mm", 0) for el in elements), default=25)
            height_mm = max(30.0, max_y + 5)

        for element in elements:
            element["x_mm"] = max(0.0, min(float(element.get("x_mm", 0)), max(0.0, width_mm - 0.1)))
            element["y_mm"] = max(0.0, min(float(element.get("y_mm", 0)), max(0.0, height_mm - 0.1)))
            element["w_mm"] = max(0.1, min(float(element.get("w_mm", 1)), width_mm - element["x_mm"]))
            element["h_mm"] = max(0.1, min(float(element.get("h_mm", 1)), height_mm - element["y_mm"]))

        warnings = []
        if not width_dots:
            warnings.append(_("El ZPL no contiene ^PW; el ancho fue inferido de los objetos."))
        if not height_dots:
            warnings.append(_("El ZPL no contiene ^LL; el alto fue inferido de los objetos."))
        if unsupported:
            warnings.append(_(
                "El ZPL contiene comandos que no pueden reconstruirse exactamente como objetos editables: %s",
                ", ".join(unsupported),
            ))
        if preview_truncated:
            warnings.append(_(
                "El ZPL contiene %(count)s objetos visuales. La vista editable se limitó a %(max)s; "
                "el ZPL original se conserva completo en modo RAW.",
                count=visual_count, max=MAX_IMPORT_ELEMENTS,
            ))

        return {
            "design": {"version": 2, "elements": elements},
            "width_mm": round(width_mm, 3),
            "height_mm": round(height_mm, 3),
            "dpi": dpi,
            "unsupported": unsupported,
            "warnings": warnings,
            "fully_editable": not unsupported and not preview_truncated,
            "preview_truncated": preview_truncated,
            "visual_count": visual_count,
        }

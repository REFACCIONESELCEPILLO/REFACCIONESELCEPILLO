# -*- coding: utf-8 -*-

import html
import re
import textwrap

from markupsafe import Markup
from reportlab.graphics.barcode.code128 import Code128

from odoo import models



class AutoPartVehicleLabelRenderer(models.AbstractModel):
    """Canonical autopart-label composition + language renderers.

    The important design rule is that *layout is resolved exactly once* in
    millimetres. Preview, ZPL and TSPL consume the same semantic plan. Printer
    quirks (direction and origin) come from the compatibility profile and are
    never hard-coded into the product layout.
    """

    _name = "sh.auto.part.vehicle.label.renderer"
    _description = "Auto Part Vehicle Label Renderer"

    FORMAT_50_30 = "auto_part_zpl_50_30"
    FORMAT_70_50 = "auto_part_zpl_70_50"

    LAYOUTS = {
        FORMAT_50_30: {
            "label": "Etiqueta de autoparte - 50 x 30 mm",
            "width_mm": 50.0,
            "height_mm": 30.0,
            # Physical acceptance on 4B-2054L (1, 3 and 10 labels) proved
            # media advance is stable.  The remaining issue was purely visual:
            # too little top safety margin and text sizes below practical
            # readability.  Keep geometry canonical and use the lower unused
            # half of the label instead of compensating with printer offsets.
            "code": {"x": 0.8, "y": 5.45, "w": 48.4, "font_mm": 3.0},
            "name": {
                "x": 0.8, "y": 10.0, "w": 48.4,
                "font_mm": 2.45, "max_lines": 2, "line_gap_mm": 2.85,
                # Wrap against the real cell pitch of resident TSPL font 2
                # with safety margin for compatible/cloned interpreters. This
                # keeps the complete name visible on the physical 50x30 label
                # instead of trusting proportional-font estimates.
                "wrap_char_mm": 1.60,
            },
            "oem": {
                "x": 0.8, "y": 16.4, "w": 48.4,
                # With up to four OEM rows there is enough vertical room to
                # use resident TSPL font 2 (physically legible). Dense labels
                # automatically fall back to font 1 through the compact style.
                "font_mm": 2.35, "max_rows": 7, "line_gap_mm": 2.80,
                "compact_after": 4,
                "compact_font_mm": 1.55,
                "compact_line_gap_mm": 1.75,
            },
            "max_oem": 7,
            "barcode": None,
        },
        FORMAT_70_50: {
            "label": "Etiqueta de autoparte - 70 x 50 mm",
            "width_mm": 70.0,
            "height_mm": 50.0,
            "code": {"x": 2.0, "y": 3.0, "w": 66.0, "font_mm": 2.5},
            "name": {
                "x": 2.0, "y": 10.5, "w": 66.0,
                "font_mm": 2.0, "max_lines": 2, "line_gap_mm": 2.8,
            },
            "oem": {
                "x": 2.0, "y": 18.5, "w": 31.0, "x2": 36.5,
                "font_mm": 1.75, "max_rows": 4, "line_gap_mm": 3.0,
                "columns": 2,
            },
            "max_oem": 8,
            "barcode": {"x": 9.0, "y": 32.0, "w": 52.0, "h": 7.5},
            "barcode_text": {"x": 2.0, "y": 41.0, "w": 66.0, "font_mm": 1.7},
        },
    }

    TSPL_FIXED_FONTS = {
        "1": (8, 12),
        "2": (12, 20),
        "3": (16, 24),
        "4": (24, 32),
        "5": (32, 48),
    }

    # ------------------------------------------------------------------
    # Data + canonical layout plan
    # ------------------------------------------------------------------

    def get_spec(self, print_format):
        return self.LAYOUTS.get(print_format, self.LAYOUTS[self.FORMAT_70_50])

    def get_record_data(self, record):
        if record._name == "product.product":
            product = record
            template = record.product_tmpl_id
            code = product.default_code or ""
            barcode = product.barcode or ""
            name = product.with_context(display_default_code=False).display_name or template.name or ""
        else:
            template = record
            product = template.product_variant_id if template.product_variant_count == 1 else False
            code = getattr(template, "default_code", False) or (product.default_code if product else "") or ""
            barcode = getattr(template, "barcode", False) or (product.barcode if product else "") or ""
            name = template.name or ""

        oem = []
        for line in template.vehicle_oem_lines.sorted(lambda rec: rec.id or 0):
            value = (line.name or "").strip()
            if not value:
                continue
            oem.append({"brand": self._get_oem_brand(line) or "Por definir", "code": value})

        return {
            "code": str(code or "").strip(),
            "name": str(name or "").strip(),
            "barcode": str(barcode or code or "").strip(),
            "oem": oem,
            "record": record,
            "template": template,
        }

    def build_plan(self, data, print_format):
        """Resolve one immutable semantic plan in millimetres.

        There are no TSPL-only or ZPL-only coordinate overrides here. Language
        renderers may choose a resident font that best matches ``font_mm``, but
        they may not move content to a different logical position.
        """
        spec = self.get_spec(print_format)
        plan = {
            "width_mm": spec["width_mm"],
            "height_mm": spec["height_mm"],
            "label": spec["label"],
            "elements": [],
        }

        code = data.get("code") or "SIN SKU"
        c = spec["code"]
        plan["elements"].append({
            "type": "text", "role": "code", "text": f"SKU: {code}", **c,
        })

        name_spec = spec["name"]
        name_lines = self._wrap_for_physical_width(
            data.get("name") or "SIN NOMBRE",
            name_spec["w"], name_spec["font_mm"], name_spec["max_lines"],
            char_width_mm=name_spec.get("wrap_char_mm"),
        )
        for index, line in enumerate(name_lines):
            plan["elements"].append({
                "type": "text", "role": "name", "text": line,
                "x": name_spec["x"],
                "y": name_spec["y"] + index * name_spec["line_gap_mm"],
                "w": name_spec["w"],
                "font_mm": name_spec["font_mm"],
            })

        oem_spec = spec["oem"]
        entries = self._visible_oems(data.get("oem") or [], spec["max_oem"])
        columns = int(oem_spec.get("columns", 1))
        compact_after = int(oem_spec.get("compact_after", 0) or 0)
        compact = bool(compact_after and len(entries) > compact_after)
        oem_font_mm = (
            float(oem_spec.get("compact_font_mm", oem_spec["font_mm"]))
            if compact else float(oem_spec["font_mm"])
        )
        oem_line_gap_mm = (
            float(oem_spec.get("compact_line_gap_mm", oem_spec["line_gap_mm"]))
            if compact else float(oem_spec["line_gap_mm"])
        )
        for index, entry in enumerate(entries):
            row, col = divmod(index, columns)
            x = oem_spec["x"] if col == 0 else oem_spec.get("x2", oem_spec["x"])
            plan["elements"].append({
                "type": "text", "role": "oem", "text": self._oem_display(entry),
                "x": x,
                "y": oem_spec["y"] + row * oem_line_gap_mm,
                "w": oem_spec["w"],
                "font_mm": oem_font_mm,
                "density": "compact" if compact else "normal",
            })

        barcode_spec = spec.get("barcode")
        if barcode_spec and data.get("barcode"):
            plan["elements"].append({
                "type": "barcode", "role": "barcode", "value": data["barcode"], **barcode_spec,
            })
            bt = spec["barcode_text"]
            plan["elements"].append({
                "type": "text", "role": "barcode_text", "text": data["barcode"], **bt,
            })

        self._validate_plan_bounds(plan)
        return plan

    def _validate_plan_bounds(self, plan):
        width, height = plan["width_mm"], plan["height_mm"]
        for element in plan["elements"]:
            x = float(element.get("x", 0.0))
            y = float(element.get("y", 0.0))
            w = float(element.get("w", 0.0))
            h = float(element.get("h", element.get("font_mm", 0.0)))
            if x < 0 or y < 0 or x + w > width + 0.01 or y + h > height + 0.01:
                raise ValueError("Elemento de etiqueta fuera del área física: %r" % element)

    # ------------------------------------------------------------------
    # Preview – consumes the canonical plan
    # ------------------------------------------------------------------

    def build_preview_html(self, record, print_format, dpi=203, company=None, selected_count=1):
        company = company or self.env.company
        data = self.get_record_data(record)
        plan = self.build_plan(data, print_format)
        svg = self._build_preview_svg(plan, company)
        messages = []
        overflow = max(0, len(data["oem"]) - self.get_spec(print_format)["max_oem"])
        if selected_count > 1:
            messages.append("Vista previa del primer producto de %s seleccionados." % selected_count)
        if overflow:
            messages.append("Hay %s referencia(s) OEM adicional(es) no visibles en este formato." % overflow)
        notice = ""
        if messages:
            notice = '<div style="margin-top:8px;padding:8px 10px;border:1px solid #d6a100;border-radius:4px;background:#fff8d8;color:#5d4a00;font-size:13px;">%s</div>' % "<br/>".join(html.escape(m) for m in messages)
        return Markup(f"""
            <div style="max-width:780px;margin:4px auto 10px auto;">
              <div style="display:flex;justify-content:space-between;margin-bottom:6px;gap:12px;">
                <strong>Vista previa — {html.escape(plan['label'])}</strong>
                <span style="font-size:12px;color:#666;">{int(dpi)} dpi</span>
              </div>
              <div style="background:#eef1f4;padding:14px;border-radius:8px;overflow:auto;">{svg}</div>
              {notice}
            </div>
        """)

    def _build_preview_svg(self, plan, company):
        nodes = ['<rect x="0" y="0" width="100%" height="100%" fill="white"/>']
        for element in plan["elements"]:
            if element["type"] == "text":
                text = html.escape(element["text"])
                weight = "700" if element.get("role") == "code" else "600" if element.get("role") == "name" else "400"
                nodes.append(
                    f'<text x="{element["x"]}" y="{element["y"] + element["font_mm"]}" '
                    f'font-family="DejaVu Sans,Arial,sans-serif" font-size="{element["font_mm"]}" '
                    f'font-weight="{weight}">{text}</text>'
                )
            elif element["type"] == "barcode":
                nodes.append(self._preview_code128_svg(element["value"], element["x"], element["y"], element["w"], element["h"]))
        width, height = plan["width_mm"], plan["height_mm"]
        return f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} {height}" style="display:block;width:min(100%,{int(width*10)}px);height:auto;margin:auto;background:white;border:1px solid #9aa0a6;box-shadow:0 2px 8px rgba(0,0,0,.15);">{''.join(nodes)}</svg>'''

    # ------------------------------------------------------------------
    # ZPL – consumes the canonical plan
    # ------------------------------------------------------------------

    def render_zpl_job(self, records_with_qty, print_format, dpi=203, company=None, printer=None):
        company = company or self.env.company
        dpi = int(dpi or 203)
        chunks = []
        for record, quantity in records_with_qty:
            data = self.get_record_data(record)
            plan = self.build_plan(data, print_format)
            for _ in range(max(0, int(quantity or 0))):
                chunks.append(self._render_one_zpl(plan, dpi, printer=printer))
        return "".join(chunks)

    def _render_one_zpl(self, plan, dpi, printer=None):
        dot = lambda mm: self._mm_to_dots(mm, dpi)
        if printer and hasattr(printer, "_ickab_zpl_preamble"):
            out = [printer._ickab_zpl_preamble(plan["width_mm"], plan["height_mm"], dpi=dpi)]
        else:
            out = [
                "^XA\n", "^CI28\n", f"^PW{dot(plan['width_mm'])}\n", f"^LL{dot(plan['height_mm'])}\n",
                "^LH0,0\n", "^LT0\n", "^LS0\n",
            ]
        for element in plan["elements"]:
            if element["type"] == "text":
                value = self._zpl_safe(element["text"])
                font_h = max(8, dot(element["font_mm"]))
                font_w = max(5, min(font_h, int(dot(element["w"]) / max(1, len(value)))))
                out.append(f"^FO{dot(element['x'])},{dot(element['y'])}^A0N,{font_h},{font_w}^FD{value}^FS\n")
            elif element["type"] == "barcode":
                value = self._zpl_safe(element["value"])
                module = self._barcode_module_width_mm(element["w"], dpi, value)
                out.append(f"^BY{module},2,{dot(element['h'])}\n^FO{dot(element['x'])},{dot(element['y'])}^BCN,{dot(element['h'])},N,N,N^FD{value}^FS\n")
        out.append("^XZ\n")
        return "".join(out)

    # ------------------------------------------------------------------
    # TSPL – consumes the same canonical plan + printer/media profile
    # ------------------------------------------------------------------

    def render_tspl_job(self, records_with_qty, print_format, dpi=203, company=None, printer=None, paper=None):
        company = company or self.env.company
        dpi = int(dpi or 203)
        profile = printer.compatibility_profile_id if printer else False
        plan0 = self.build_plan({"code": "", "name": "", "barcode": "", "oem": []}, print_format)
        if printer and hasattr(printer, "_ickab_tspl_preamble"):
            preamble = printer._ickab_tspl_preamble(
                plan0["width_mm"], plan0["height_mm"], paper=paper, include_codepage=True
            ).encode("ascii")
        else:
            preamble = self._tspl_header(plan0, paper=paper, profile=profile)
        chunks = [preamble]
        for record, quantity in records_with_qty:
            quantity = max(0, int(quantity or 0))
            if not quantity:
                continue
            plan = self.build_plan(self.get_record_data(record), print_format)
            chunks.append(self._render_one_tspl(plan, dpi, company, profile, copies=quantity))
        return b"".join(chunks)

    def _tspl_header(self, plan, paper=None, profile=None):
        gap = float(getattr(paper, "gap_mm", 2.0) if paper else 2.0)
        offset = float(getattr(paper, "gap_offset_mm", 0.0) if paper else 0.0)
        if paper and getattr(paper, "sensor_mode", "gap") == "blackmark":
            media = f"BLINE {gap:g} mm,{offset:g} mm"
        elif paper and getattr(paper, "sensor_mode", "gap") == "continuous":
            media = "GAP 0 mm,0 mm"
        else:
            media = f"GAP {gap:g} mm,{offset:g} mm"
        direction = getattr(profile, "label_direction", "1") if profile else "1"
        ref_x = int(getattr(profile, "origin_x_dots", 0) or 0) if profile else 0
        ref_y = int(getattr(profile, "origin_y_dots", 0) or 0) if profile else 0
        return (
            f"SIZE {plan['width_mm']:g} mm,{plan['height_mm']:g} mm\r\n"
            f"{media}\r\n"
            f"DIRECTION {direction or '1'}\r\n"
            f"REFERENCE {ref_x},{ref_y}\r\n"
            "CODEPAGE 850\r\n"
        ).encode("ascii")

    def _render_one_tspl(self, plan, dpi, company, profile, copies=1):
        out = [b"CLS\r\n"]
        # Text/barcode come first. This guarantees core product data is generated
        # independently from optional graphics and makes failures diagnosable.
        for element in plan["elements"]:
            if element["type"] == "text":
                out.append(self._tspl_text_command(element, dpi, profile))
            elif element["type"] == "barcode":
                value = self._tspl_safe(element["value"])
                narrow = self._tspl_barcode_module_width(value, element["w"], dpi)
                out.append(self._tspl_ascii(
                    f'BARCODE {self._mm_to_dots(element["x"], dpi)},{self._mm_to_dots(element["y"], dpi)},'
                    f'"128",{self._mm_to_dots(element["h"], dpi)},0,0,{narrow},{narrow},"{value}"\r\n'
                ))


        out.append(f"PRINT 1,{max(1, int(copies or 1))}\r\n".encode("ascii"))
        return b"".join(out)

    def _tspl_text_command(self, element, dpi, profile=None):
        """Render one text element without changing its canonical position.

        TSPL2 models that explicitly advertise the scalable internal font 0 can
        reproduce the semantic font hierarchy much more closely. Plain TSPL or
        unknown clones fall back to the fixed 1..5 fonts.
        """
        x = self._mm_to_dots(element["x"], dpi)
        y = self._mm_to_dots(element["y"], dpi)
        text = self._tspl_safe(element["text"])
        if profile and getattr(profile, "tspl_scalable_font0", False):
            point_size = max(3, min(10, int(round(float(element.get("font_mm", 1.4)) * 72.0 / 25.4))))
            return self._tspl_ascii(
                f'TEXT {x},{y},"0",0,{point_size},{point_size},"{text}"\r\n'
            )
        font = self._tspl_font_for_element(element, dpi)
        return self._tspl_ascii(f'TEXT {x},{y},"{font}",0,1,1,"{text}"\r\n')

    def _tspl_font_for_element(self, element, dpi):
        text = self._tspl_safe(element.get("text"))
        area = self._mm_to_dots(element.get("w", 1.0), dpi)
        target_h = self._mm_to_dots(element.get("font_mm", 1.4), dpi)
        # Smallest-first for name/OEM keeps 50x30 readable and deterministic.
        preferred = ("1", "2", "3", "4", "5") if element.get("role") in ("name", "oem") else ("2", "1", "3")
        candidates = []
        for font in preferred:
            fw, fh = self.TSPL_FIXED_FONTS[font]
            if len(text) * fw <= area:
                candidates.append((abs(fh - target_h), font))
        if candidates:
            return min(candidates)[1]
        return "1"

    # ------------------------------------------------------------------
    # Shared helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _wrap_for_physical_width(value, width_mm, font_mm, max_lines, char_width_mm=None):
        value = re.sub(r"\s+", " ", str(value or "")).strip() or "SIN NOMBRE"
        # For resident thermal-printer fonts, character pitch is more reliable
        # than a proportional-font heuristic. Layouts may provide a conservative
        # cell width measured/validated on physical hardware. Other formats keep
        # the generic estimate.
        avg = float(char_width_mm) if char_width_mm else max(0.55, float(font_mm) * 0.62)
        capacity = max(8, int(float(width_mm) / avg))
        lines = textwrap.wrap(value, width=capacity, break_long_words=True, break_on_hyphens=True) or [value]
        if len(lines) > max_lines:
            lines = lines[:max_lines]
            last = lines[-1]
            if len(last) >= capacity:
                last = last[: max(1, capacity - 3)]
            lines[-1] = last.rstrip(" .") + "..."
        return lines

    @staticmethod
    def _visible_oems(oems, max_oem):
        if len(oems) <= max_oem:
            return list(oems)
        visible = list(oems[: max_oem - 1])
        visible.append({"brand": "", "code": f"+{len(oems) - (max_oem - 1)} REF."})
        return visible

    @staticmethod
    def _oem_display(entry):
        brand = (entry.get("brand") or "").strip()
        code = (entry.get("code") or "").strip()
        return f"{brand}: {code}" if brand else code

    @staticmethod
    def _get_oem_brand(line):
        for name in ("brand_id", "manufacturer_id", "vehicle_brand_id"):
            field = getattr(line, name, False)
            if field:
                return str(field.display_name or "").strip()
        for name in ("brand", "manufacturer", "make"):
            value = getattr(line, name, False)
            if value:
                return str(value.display_name if hasattr(value, "_name") else value).strip()
        return ""

    @staticmethod
    def _mm_to_dots(mm, dpi):
        return max(0, int(round(float(mm) * float(dpi) / 25.4)))

    @staticmethod
    def _zpl_safe(value):
        value = re.sub(r"[\r\n\t]+", " ", str(value or ""))
        value = re.sub(r"\s+", " ", value).strip()
        return value.replace("^", " ").replace("~", " ")

    @staticmethod
    def _tspl_safe(value):
        value = re.sub(r"[\r\n\t]+", " ", str(value or ""))
        value = re.sub(r"\s+", " ", value).strip()
        return value.replace('"', "'")

    @staticmethod
    def _tspl_ascii(value):
        return str(value).encode("cp850", errors="replace")

    @staticmethod
    def _tspl_barcode_module_width(value, area_width_mm, dpi):
        modules = (11 * (len(str(value or "")) + 3)) + 13 + 20
        area_dots = max(1, int(round(float(area_width_mm) * float(dpi) / 25.4)))
        return 2 if modules * 2 <= area_dots else 1

    @staticmethod
    def _barcode_module_width_mm(area_width_mm, dpi, value):
        modules = (11 * (len(str(value or "")) + 3)) + 13 + 20
        area = max(1, int(round(float(area_width_mm) * float(dpi) / 25.4)))
        return 2 if modules * 2 <= area else 1

    def _preview_code128_svg(self, value, x_mm, y_mm, width_mm, height_mm):
        value = str(value or "").strip()
        if not value:
            return ""
        try:
            barcode = Code128(value=value, quiet=0)
            barcode.validate()
            if not barcode.valid:
                return ""
            barcode.encode()
            pattern = barcode.decompose()
        except Exception:
            return ""

        def symbol_width(symbol):
            if "A" <= symbol <= "D":
                return ord(symbol) - ord("A") + 1
            if "a" <= symbol <= "d":
                return ord(symbol) - ord("a") + 1
            return 0

        quiet = 10
        total = sum(symbol_width(s) for s in pattern) + quiet * 2
        if not total:
            return ""
        module = float(width_mm) / float(total)
        cursor = float(x_mm) + quiet * module
        rects = []
        for symbol in pattern:
            sw = symbol_width(symbol)
            if not sw:
                continue
            w = sw * module
            if symbol.isupper():
                rects.append(f'<rect x="{cursor:.4f}" y="{y_mm}" width="{w:.4f}" height="{height_mm}" fill="black"/>')
            cursor += w
        return '<g class="o_auto_part_code128">%s</g>' % "".join(rects)

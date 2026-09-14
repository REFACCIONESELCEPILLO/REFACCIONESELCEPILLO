# Copyright 2026 ICKAB. All rights reserved.
import json


def migrate(cr, version):
    """Convert legacy percentage-based designs to physical millimetres.

    Runtime code can still read v1, so this migration is deliberately best-effort:
    malformed rows are left untouched instead of jeopardizing the module upgrade.
    """
    cr.execute("SELECT id, width_mm, height_mm, dpi, design_json FROM ickab_label_template")
    for record_id, width_mm, height_mm, dpi, raw in cr.fetchall():
        try:
            data = json.loads(raw or "{}")
            if int(data.get("version", 1) or 1) != 1:
                continue
            width = float(width_mm or 50)
            height = float(height_mm or 30)
            target_dpi = int(dpi or 203)
            elements = []
            for index, legacy in enumerate(data.get("elements") or [], start=1):
                if not isinstance(legacy, dict):
                    continue
                element = dict(legacy)
                element["x_mm"] = round(float(legacy.get("x", 0) or 0) * width / 100.0, 4)
                element["y_mm"] = round(float(legacy.get("y", 0) or 0) * height / 100.0, 4)
                element["w_mm"] = round(float(legacy.get("w", 20) or 20) * width / 100.0, 4)
                element["h_mm"] = round(float(legacy.get("h", 10) or 10) * height / 100.0, 4)
                element["z"] = int(legacy.get("z", index) or index)
                if element.get("type") in {"box", "line"}:
                    element["thickness_mm"] = max(
                        0.1,
                        float(legacy.get("thickness", 2) or 2) * 25.4 / target_dpi,
                    )
                if element.get("type") == "line":
                    element.setdefault("line_direction", "horizontal")
                for old in ("x", "y", "w", "h", "thickness"):
                    element.pop(old, None)
                elements.append(element)
            data["version"] = 2
            data["elements"] = elements
            cr.execute(
                "UPDATE ickab_label_template SET design_json=%s WHERE id=%s",
                (json.dumps(data, ensure_ascii=False), record_id),
            )
        except Exception:
            continue

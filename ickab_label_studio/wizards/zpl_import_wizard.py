# Copyright 2026 ICKAB. All rights reserved.
import base64
import json

from odoo import _, api, fields, models
from odoo.exceptions import UserError


class IckabLabelZplImportWizard(models.TransientModel):
    _name = "ickab.label.zpl.import.wizard"
    _description = "Importar ZPL a ICKAB Label Studio"

    target_template_id = fields.Many2one("ickab.label.template", string="Diseño a reemplazar", ondelete="cascade")
    template_name = fields.Char(string="Nombre del diseño", required=True, default="ZPL importado")
    model_id = fields.Many2one(
        "ir.model",
        string="Modelo de datos",
        domain=[("transient", "=", False)],
        ondelete="set null",
        help="Opcional. Sólo es necesario si después asignará campos dinámicos de Odoo.",
    )
    source_dpi = fields.Selection(
        [("203", "203 DPI"), ("300", "300 DPI"), ("600", "600 DPI")],
        string="DPI del ZPL de origen",
        default="203",
        required=True,
    )
    import_mode = fields.Selection(
        [
            ("auto", "Automático (recomendado)"),
            ("editable", "Diseño editable (sólo si es seguro)"),
            ("raw", "Conservar ZPL RAW exacto"),
        ],
        default="auto",
        required=True,
        help=(
            "Automático crea un diseño editable sólo si la reconstrucción es segura. "
            "Si hay comandos desconocidos o semántica no reversible conserva el ZPL RAW. "
            "La opción editable nunca descarta comandos no soportados."
        ),
    )
    zpl_file = fields.Binary(string="Archivo .zpl", attachment=False)
    zpl_filename = fields.Char(string="Nombre de archivo")
    source_zpl = fields.Text(string="Código ZPL")

    @api.onchange("zpl_file")
    def _onchange_zpl_file(self):
        if not self.zpl_file:
            return
        try:
            raw = base64.b64decode(self.zpl_file)
            try:
                self.source_zpl = raw.decode("utf-8-sig")
            except UnicodeDecodeError:
                self.source_zpl = raw.decode("latin-1")
            if self.zpl_filename and (not self.template_name or self.template_name == "ZPL importado"):
                self.template_name = self.zpl_filename.rsplit(".", 1)[0]
        except Exception:
            self.source_zpl = False

    def action_import(self):
        self.ensure_one()
        if not str(self.source_zpl or "").strip():
            raise UserError(_("Pegue o cargue código ZPL antes de importar."))
        parsed = self.env["ickab.label.zpl.parser"].parse(self.source_zpl, dpi=int(self.source_dpi))
        final_mode = self.import_mode
        if final_mode == "auto":
            final_mode = "editable" if parsed["fully_editable"] else "raw"
        elif final_mode == "editable" and not parsed["fully_editable"]:
            details = ", ".join(parsed.get("unsupported") or []) or _("contenido no convertible")
            raise UserError(_(
                "No es seguro forzar este ZPL a modo editable porque contiene %(details)s. "
                "Use importación Automática o RAW para conservar el original sin pérdida.",
                details=details,
            ))

        vals = {
            "name": self.template_name,
            "model_id": self.model_id.id or False,
            "width_mm": parsed["width_mm"],
            "height_mm": parsed["height_mm"],
            "dpi": self.source_dpi,
            "shape": "rectangle",
            "design_json": json.dumps(parsed["design"], ensure_ascii=False),
            "document_mode": "studio" if final_mode == "editable" else "zpl_raw",
            "source_zpl": self.source_zpl,
            "zpl_import_warnings": "\n".join(parsed["warnings"]),
            "zpl_source_dpi": self.source_dpi,
        }
        if self.target_template_id:
            template = self.target_template_id
            template.check_access("write")
            template.write(vals)
        else:
            template = self.env["ickab.label.template"].create(vals)
        return {
            "type": "ir.actions.act_window",
            "res_model": "ickab.label.template",
            "res_id": template.id,
            "view_mode": "form",
            "target": "current",
        }

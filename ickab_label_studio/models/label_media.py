# Copyright 2026 ICKAB. All rights reserved.
import re

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


class IckabLabelMedia(models.Model):
    _name = "ickab.label.media"
    _description = "ICKAB Label Media"
    _order = "category, width_mm, height_mm, name"

    name = fields.Char(string="Nombre", required=True, translate=True)
    code = fields.Char(string="Código", required=True, index=True, copy=False)
    active = fields.Boolean(default=True)
    category = fields.Selection(
        [
            ("general", "General"),
            ("product", "Producto"),
            ("shipping", "Paquetería"),
            ("circular", "Circular / ovalada"),
        ],
        default="general",
        required=True,
    )
    shape = fields.Selection(
        [
            ("rectangle", "Rectangular"),
            ("square", "Cuadrada"),
            ("circle", "Circular"),
            ("oval", "Ovalada"),
        ],
        default="rectangle",
        required=True,
    )
    width_mm = fields.Float(string="Ancho (mm)", required=True)
    height_mm = fields.Float(string="Alto (mm)", required=True)
    media_type = fields.Selection(
        [("gap", "Gap"), ("blackmark", "Marca negra"), ("continuous", "Continuo")],
        string="Sensor / medio",
        default="gap",
        required=True,
    )
    gap_mm = fields.Float(string="Gap (mm)", default=2.0)
    gap_offset_mm = fields.Float(string="Offset de gap (mm)", default=0.0)
    safe_margin_mm = fields.Float(string="Margen seguro (mm)", default=1.5)
    bleed_mm = fields.Float(string="Sangrado (mm)", default=0.0)
    notes = fields.Text(string="Notas")

    _sql_constraints = [
        ("code_uniq", "unique(code)", "El código del formato debe ser único."),
    ]

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if "code" in vals:
                vals["code"] = str(vals["code"] or "").strip().lower()
        return super().create(vals_list)

    def write(self, vals):
        if "code" in vals:
            vals = dict(vals, code=str(vals["code"] or "").strip().lower())
        return super().write(vals)

    @api.constrains("code")
    def _check_code(self):
        for rec in self:
            code = str(rec.code or "").strip().lower()
            if not re.fullmatch(r"[a-z0-9][a-z0-9_.-]{1,63}", code):
                raise ValidationError(_("El código del formato sólo puede contener letras, números, punto, guion y guion bajo."))

    @api.constrains("width_mm", "height_mm", "gap_mm", "safe_margin_mm", "bleed_mm", "shape")
    def _check_geometry(self):
        for rec in self:
            if not 0 < rec.width_mm <= 1000 or not 0 < rec.height_mm <= 1000:
                raise ValidationError(_("El formato debe medir entre 0 y 1000 mm por lado."))
            if rec.gap_mm < 0 or rec.safe_margin_mm < 0 or rec.bleed_mm < 0:
                raise ValidationError(_("Gap, margen seguro y sangrado no pueden ser negativos."))
            if rec.safe_margin_mm * 2 >= min(rec.width_mm, rec.height_mm):
                raise ValidationError(_("El margen seguro deja el formato sin área útil."))
            if rec.shape in {"circle", "square"} and abs(rec.width_mm - rec.height_mm) > 0.01:
                raise ValidationError(_("Los formatos circulares y cuadrados requieren ancho y alto iguales."))

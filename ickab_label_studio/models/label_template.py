# Copyright 2026 ICKAB. All rights reserved.
import json
import re
import uuid
from math import isfinite
from urllib.parse import urlencode

from odoo import _, api, fields, models
from odoo.exceptions import AccessError, UserError, ValidationError


ALLOWED_ELEMENT_TYPES = {"text", "barcode", "qrcode", "box", "line"}
ALLOWED_SOURCES = {"static", "field"}
ALLOWED_ALIGNMENTS = {"L", "C", "R", "J"}
ALLOWED_BARCODES = {"code128", "code39", "ean13", "upca"}
ALLOWED_LINE_DIRECTIONS = {"horizontal", "vertical"}
RELATIONAL_TYPES = {"many2one", "one2many", "many2many", "reference"}
MAX_ELEMENTS = 500
MAX_FIELD_DEPTH = 5
MAX_PREVIEW_LABELS = 200
MAX_DESIGN_BYTES = 1024 * 1024
MAX_LITERAL_CHARS = 32768
MAX_RENDERED_CHARS = 65536
ALLOWED_AGGREGATES = {"first", "last", "join", "count"}
MAX_COLLECTION_ITEMS = 500


def _default_design():
    # A new label must always be valid regardless of its physical size.  Demo
    # objects belong in documentation, not in the canonical document.
    return {"version": 2, "elements": []}


class IckabLabelTemplate(models.Model):
    _name = "ickab.label.template"
    _description = "ICKAB Label Template"
    _order = "name, id"

    name = fields.Char(string="Nombre", required=True, translate=True)
    technical_key = fields.Char(
        string="Clave técnica",
        default=lambda self: uuid.uuid4().hex,
        readonly=True,
        copy=False,
        index=True,
    )
    active = fields.Boolean(default=True)
    company_id = fields.Many2one(
        "res.company",
        string="Compañía",
        default=lambda self: self.env.company,
        index=True,
        ondelete="cascade",
        help="Déjelo vacío para compartir el diseño entre compañías permitidas.",
    )
    model_id = fields.Many2one(
        "ir.model",
        string="Modelo de datos",
        index=True,
        domain=[("transient", "=", False)],
        ondelete="set null",
        help="Opcional. Modelo Odoo cuyos registros alimentan los campos dinámicos de la etiqueta.",
    )
    media_id = fields.Many2one(
        "ickab.label.media",
        string="Formato de etiqueta",
        ondelete="set null",
        help="Perfil físico reutilizable. Puede dejarlo vacío y usar dimensiones personalizadas.",
    )
    shape = fields.Selection(
        [
            ("rectangle", "Rectangular"),
            ("square", "Cuadrada"),
            ("circle", "Circular"),
            ("oval", "Ovalada"),
        ],
        string="Forma",
        default="rectangle",
        required=True,
    )
    width_mm = fields.Float(string="Ancho (mm)", default=50.0, required=True)
    height_mm = fields.Float(string="Alto (mm)", default=30.0, required=True)
    dpi = fields.Selection(
        [("203", "203 DPI"), ("300", "300 DPI"), ("600", "600 DPI")],
        string="DPI de referencia",
        default="203",
        required=True,
        help="DPI usado para previsualizar/exportar ZPL. El diseño maestro siempre se almacena en milímetros.",
    )
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
    document_mode = fields.Selection(
        [("studio", "Diseño editable"), ("zpl_raw", "ZPL RAW")],
        string="Modo de documento",
        default="studio",
        required=True,
    )
    source_zpl = fields.Text(
        string="ZPL original",
        help="Fuente ZPL importada. En modo RAW se conserva y se exporta sin reinterpretar el diseño.",
    )
    zpl_source_dpi = fields.Selection(
        [("203", "203 DPI"), ("300", "300 DPI"), ("600", "600 DPI")],
        string="DPI ZPL origen",
        default="203",
    )
    zpl_import_warnings = fields.Text(string="Advertencias de importación", readonly=True)
    design_json = fields.Text(
        string="Diseño",
        default=lambda self: json.dumps(_default_design(), ensure_ascii=False),
        required=True,
    )
    notes = fields.Text(string="Notas")
    element_count = fields.Integer(string="Elementos", compute="_compute_element_count")

    _sql_constraints = [
        ("technical_key_uniq", "unique(technical_key)", "La clave técnica del diseño debe ser única."),
    ]

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            key = str(vals.get("technical_key") or uuid.uuid4().hex).strip().lower()
            if not re.fullmatch(r"[0-9a-f]{32}", key):
                raise ValidationError(_("La clave técnica debe ser un identificador hexadecimal de 32 caracteres."))
            vals["technical_key"] = key
        return super().create(vals_list)

    def write(self, vals):
        if "technical_key" in vals:
            new_key = str(vals.get("technical_key") or "").strip().lower()
            if not re.fullmatch(r"[0-9a-f]{32}", new_key):
                raise ValidationError(_("La clave técnica debe ser un identificador hexadecimal de 32 caracteres."))
            vals = dict(vals, technical_key=new_key)
            for record in self:
                if record.technical_key and record.technical_key != new_key:
                    raise ValidationError(_("La clave técnica de un diseño existente no puede modificarse."))
        return super().write(vals)

    @api.onchange("media_id")
    def _onchange_media_id(self):
        if not self.media_id:
            return
        media = self.media_id
        self.shape = media.shape
        self.width_mm = media.width_mm
        self.height_mm = media.height_mm
        self.media_type = media.media_type
        self.gap_mm = media.gap_mm
        self.gap_offset_mm = media.gap_offset_mm
        self.safe_margin_mm = media.safe_margin_mm
        self.bleed_mm = media.bleed_mm

    @api.onchange("shape", "width_mm")
    def _onchange_equal_sides(self):
        if self.shape in {"circle", "square"} and self.width_mm > 0:
            self.height_mm = self.width_mm

    @api.constrains("technical_key")
    def _check_technical_key(self):
        for rec in self:
            if not re.fullmatch(r"[0-9a-f]{32}", str(rec.technical_key or "").strip().lower()):
                raise ValidationError(_("La clave técnica del diseño no es válida."))

    @api.depends("design_json")
    def _compute_element_count(self):
        for rec in self:
            rec.element_count = len(rec._parse_design(strict=False).get("elements", []))

    @api.constrains(
        "width_mm", "height_mm", "gap_mm", "gap_offset_mm", "safe_margin_mm", "bleed_mm", "shape"
    )
    def _check_geometry(self):
        for rec in self:
            for label, value in ((_("ancho"), rec.width_mm), (_("alto"), rec.height_mm)):
                if not isfinite(value) or not 0 < value <= 1000:
                    raise ValidationError(_("El %(label)s debe ser mayor que 0 y menor o igual a 1000 mm.", label=label))
            if not isfinite(rec.gap_mm) or rec.gap_mm < 0:
                raise ValidationError(_("El gap no puede ser negativo."))
            if not isfinite(rec.gap_offset_mm):
                raise ValidationError(_("El offset de gap debe ser un número válido."))
            if not isfinite(rec.safe_margin_mm) or rec.safe_margin_mm < 0:
                raise ValidationError(_("El margen seguro no puede ser negativo."))
            if not isfinite(rec.bleed_mm) or rec.bleed_mm < 0:
                raise ValidationError(_("El sangrado no puede ser negativo."))
            if rec.safe_margin_mm * 2 >= min(rec.width_mm, rec.height_mm):
                raise ValidationError(_("El margen seguro deja la etiqueta sin área útil."))
            if rec.shape in {"circle", "square"} and abs(rec.width_mm - rec.height_mm) > 0.01:
                raise ValidationError(_("Las etiquetas circulares y cuadradas requieren ancho y alto iguales."))

    @api.constrains("design_json", "model_id", "width_mm", "height_mm")
    def _check_design_json(self):
        for rec in self:
            rec._parse_design(strict=True, validate_fields=True)

    def _convert_v1_to_v2(self, data):
        """Normalize the legacy percentage schema to physical millimetres.

        The conversion is deterministic and uses the template's current physical size.
        Existing 18.0.2.x designs therefore remain usable without a destructive migration.
        """
        elements = []
        for index, legacy in enumerate(data.get("elements") or [], start=1):
            if not isinstance(legacy, dict):
                continue
            element = dict(legacy)
            element["x_mm"] = round(float(legacy.get("x", 0) or 0) * self.width_mm / 100.0, 4)
            element["y_mm"] = round(float(legacy.get("y", 0) or 0) * self.height_mm / 100.0, 4)
            element["w_mm"] = round(float(legacy.get("w", 20) or 20) * self.width_mm / 100.0, 4)
            element["h_mm"] = round(float(legacy.get("h", 10) or 10) * self.height_mm / 100.0, 4)
            element["z"] = int(legacy.get("z", index) or index)
            if element.get("type") in {"box", "line"} and "thickness_mm" not in element:
                # v1 thickness was printer-dot oriented. Convert it into a physical default.
                element["thickness_mm"] = max(0.1, float(legacy.get("thickness", 2) or 2) * 25.4 / int(self.dpi or 203))
            if element.get("type") == "line":
                element.setdefault("line_direction", "horizontal")
            for old in ("x", "y", "w", "h", "thickness"):
                element.pop(old, None)
            elements.append(element)
        return {**data, "version": 2, "elements": elements}

    def _parse_design(self, strict=False, validate_fields=False):
        self.ensure_one()
        raw_design = self.design_json or "{}"
        if len(raw_design.encode("utf-8")) > MAX_DESIGN_BYTES:
            if strict:
                raise ValidationError(_("El diseño excede el tamaño máximo permitido de 1 MB."))
            return {"version": 2, "elements": []}
        try:
            data = json.loads(raw_design)
        except (TypeError, ValueError) as exc:
            if strict:
                raise ValidationError(_("El diseño no contiene JSON válido.")) from exc
            return {"version": 2, "elements": []}
        if not isinstance(data, dict):
            if strict:
                raise ValidationError(_("El diseño debe ser un objeto JSON."))
            return {"version": 2, "elements": []}

        try:
            version = int(data.get("version", 1) or 1)
        except (TypeError, ValueError, OverflowError) as exc:
            if strict:
                raise ValidationError(_("La versión del diseño no es válida.")) from exc
            return {"version": 2, "elements": []}
        if version == 1:
            data = self._convert_v1_to_v2(data)
            version = 2
        if version != 2:
            if strict:
                raise ValidationError(_("Versión de diseño no soportada: %s", version))
            return {"version": 2, "elements": []}

        elements = data.get("elements", [])
        if not isinstance(elements, list):
            if strict:
                raise ValidationError(_("La colección de elementos debe ser una lista."))
            elements = []
        if len(elements) > MAX_ELEMENTS:
            raise ValidationError(_("El diseño excede el máximo de %(max)s elementos.", max=MAX_ELEMENTS))

        clean = []
        seen_ids = set()
        for index, element in enumerate(elements, start=1):
            if not isinstance(element, dict):
                if strict:
                    raise ValidationError(_("El elemento %(n)s no es válido.", n=index))
                continue
            normalized = dict(element)
            normalized.setdefault("z", index)
            if strict:
                self._validate_element(normalized, index, seen_ids, validate_fields=validate_fields)
            clean.append(normalized)
            element_id = str(normalized.get("id") or "")
            if element_id:
                seen_ids.add(element_id)
        return {**data, "version": 2, "elements": clean}

    def _validate_element(self, element, index, seen_ids, validate_fields=False):
        element_id = str(element.get("id") or "").strip()
        if not element_id or len(element_id) > 80 or not re.fullmatch(r"[A-Za-z0-9_.-]+", element_id):
            raise ValidationError(_("El elemento %(n)s requiere un identificador técnico válido.", n=index))
        if element_id in seen_ids:
            raise ValidationError(_("El identificador de elemento '%s' está duplicado.", element_id))

        etype = element.get("type")
        if etype not in ALLOWED_ELEMENT_TYPES:
            raise ValidationError(_("Tipo de elemento no soportado: %s", etype))

        x = self._number(element.get("x_mm", 0), _("X"))
        y = self._number(element.get("y_mm", 0), _("Y"))
        w = self._number(element.get("w_mm", 0), _("ancho del elemento"))
        h = self._number(element.get("h_mm", 0), _("alto del elemento"))
        tolerance = 0.001
        if x < 0 or y < 0 or w <= 0 or h <= 0:
            raise ValidationError(_("El elemento '%s' tiene geometría física inválida.", element_id))
        if x + w > self.width_mm + tolerance or y + h > self.height_mm + tolerance:
            raise ValidationError(_("El elemento '%s' debe quedar completamente dentro de la etiqueta.", element_id))

        try:
            int(element.get("z", index) or 0)
        except (TypeError, ValueError) as exc:
            raise ValidationError(_("La capa Z del elemento '%s' no es válida.", element_id)) from exc

        if etype in {"text", "barcode", "qrcode"}:
            source = element.get("source", "static")
            if source not in ALLOWED_SOURCES:
                raise ValidationError(_("Origen de datos no soportado en '%s'.", element_id))
            if source == "field":
                path = str(element.get("field_path") or "").strip()
                if not path:
                    raise ValidationError(_("El elemento '%s' requiere un campo Odoo.", element_id))
                if validate_fields:
                    path_info = self._field_path_info(path)
                    if path_info["collection"]:
                        aggregate = str(element.get("aggregate") or "").strip().lower()
                        if aggregate not in ALLOWED_AGGREGATES:
                            raise ValidationError(_(
                                "El elemento '%(element)s' usa una relación múltiple. "
                                "Seleccione Primero, Último, Unir o Contar.",
                                element=element_id,
                            ))
                        separator = str(element.get("separator", ", ") or "")
                        if len(separator) > 100:
                            raise ValidationError(_(
                                "El separador del elemento '%s' excede 100 caracteres.", element_id
                            ))
            else:
                literal = str(element.get("value") or "")
                if len(literal) > MAX_LITERAL_CHARS:
                    raise ValidationError(_("El texto fijo de '%s' excede el límite permitido.", element_id))

        if etype == "text":
            font_mm = self._number(element.get("font_mm", 3), _("tamaño de fuente"))
            if not 0.5 <= font_mm <= 100:
                raise ValidationError(_("El tamaño de fuente de '%s' está fuera de rango.", element_id))
            if element.get("align", "L") not in ALLOWED_ALIGNMENTS:
                raise ValidationError(_("Alineación no soportada en '%s'.", element_id))
            max_lines = int(self._number(element.get("max_lines", 1), _("líneas máximas")))
            if not 1 <= max_lines <= 100:
                raise ValidationError(_("Las líneas máximas de '%s' están fuera de rango.", element_id))
        elif etype == "barcode":
            if element.get("barcode_type", "code128") not in ALLOWED_BARCODES:
                raise ValidationError(_("Simbología no soportada en '%s'.", element_id))
        elif etype == "qrcode":
            mag = int(self._number(element.get("magnification", 4), _("magnificación QR")))
            if not 1 <= mag <= 10:
                raise ValidationError(_("La magnificación QR de '%s' debe estar entre 1 y 10.", element_id))
        elif etype in {"box", "line"}:
            thickness_mm = self._number(element.get("thickness_mm", 0.25), _("grosor"))
            if not 0.05 <= thickness_mm <= 20:
                raise ValidationError(_("El grosor de '%s' está fuera de rango.", element_id))
            if etype == "line" and element.get("line_direction", "horizontal") not in ALLOWED_LINE_DIRECTIONS:
                raise ValidationError(_("Dirección de línea no soportada en '%s'.", element_id))
            if etype == "box":
                rounding = int(self._number(element.get("rounding", 0), _("redondeo")))
                if not 0 <= rounding <= 8:
                    raise ValidationError(_("El redondeo de '%s' debe estar entre 0 y 8.", element_id))

    @staticmethod
    def _number(value, label):
        try:
            number = float(value)
        except (TypeError, ValueError) as exc:
            raise ValidationError(_("%(label)s debe ser numérico.", label=label)) from exc
        if not isfinite(number):
            raise ValidationError(_("%(label)s debe ser un número finito.", label=label))
        return number

    def _model_is_readable(self, model_name):
        if not model_name:
            return False
        try:
            model = self.env[model_name]
            return bool(model.check_access_rights("read", raise_exception=False))
        except (KeyError, AccessError):
            return False

    def _field_path_info(self, path):
        """Validate a field path and describe its relational semantics.

        The method deliberately uses the current user's ORM environment.  It never
        sudoes field metadata or business records, so Label Studio cannot become a
        side channel around Odoo ACLs/field groups.
        """
        self.ensure_one()
        if not self.model_id:
            raise ValidationError(_("Seleccione un Modelo de datos antes de usar campos dinámicos."))
        path = str(path or "").strip()
        parts = path.split(".") if path else []
        if not parts or len(parts) > MAX_FIELD_DEPTH or any(
            not part or part.startswith("_") or not re.fullmatch(r"[A-Za-z0-9_]+", part)
            for part in parts
        ):
            raise ValidationError(_("Ruta de campo no permitida: %s", path))

        model_name = self.model_id.model
        if not self._model_is_readable(model_name):
            raise AccessError(_("No tiene permiso de lectura sobre el modelo %s.", model_name))
        collection = False
        chain = []
        for index, part in enumerate(parts):
            model = self.env[model_name]
            # fields_get applies field-level groups for the current user.  Checking
            # it on every hop prevents hidden fields from being addressed manually.
            visible_defs = model.fields_get(allfields=[part], attributes=["string", "type", "relation"])
            definition = visible_defs.get(part)
            field = model._fields.get(part)
            if not field or not definition or field.type == "binary":
                raise ValidationError(_(
                    "El campo '%(field)s' no está disponible en %(model)s.",
                    field=part, model=model_name,
                ))
            is_collection = field.type in {"one2many", "many2many"}
            collection = collection or is_collection
            relation = getattr(field, "comodel_name", False) or definition.get("relation") or False
            chain.append({
                "name": part,
                "label": definition.get("string") or part,
                "type": field.type,
                "model": model_name,
                "relation": relation or "",
                "collection": is_collection,
            })
            if index < len(parts) - 1:
                if field.type not in {"many2one", "one2many", "many2many"} or not relation:
                    raise ValidationError(_(
                        "El campo '%(field)s' no permite continuar la ruta %(path)s.",
                        field=part, path=path,
                    ))
                if not self._model_is_readable(relation):
                    raise AccessError(_("No tiene permiso de lectura sobre el modelo relacionado %s.", relation))
                model_name = relation
        return {
            "path": path,
            "chain": chain,
            "collection": collection,
            "terminal_type": chain[-1]["type"],
            "terminal_model": chain[-1]["model"],
        }

    def _validate_field_path(self, path):
        self._field_path_info(path)
        return True

    def _size_dots(self, dpi=None):
        self.ensure_one()
        target_dpi = int(dpi or self.dpi or 203)
        if target_dpi not in (203, 300, 600):
            raise UserError(_("DPI no soportado: %s", target_dpi))
        return (
            max(1, round(self.width_mm * target_dpi / 25.4)),
            max(1, round(self.height_mm * target_dpi / 25.4)),
        )

    @api.model
    def _label_studio_user_allowed(self):
        return bool(
            self.env.user.has_group("ickab_label_studio.group_label_studio_user")
            or self.env.user.has_group("base.group_system")
        )

    @api.model
    def get_field_catalog(self, model_id, relation_path=""):
        """Return one level of the relational field explorer.

        ``relation_path`` is always relative to the selected base model.  The
        response contains full canonical paths, so drag & drop never depends on
        UI state after the field has been inserted into a design.
        """
        if not self._label_studio_user_allowed():
            raise AccessError(_("No tiene permisos para consultar campos de ICKAB Label Studio."))
        try:
            model_id = int(model_id)
        except (TypeError, ValueError):
            return {"fields": [], "breadcrumbs": [], "relation_path": "", "depth": 0}
        base = self.env["ir.model"].browse(model_id).exists()
        if not base or base.transient or not self._model_is_readable(base.model):
            return {"fields": [], "breadcrumbs": [], "relation_path": "", "depth": 0}

        relation_path = str(relation_path or "").strip(".")
        current_model = base.model
        breadcrumbs = [{"label": base.name or base.model, "path": "", "model": base.model}]
        collection_in_path = False
        if relation_path:
            parts = relation_path.split(".")
            if len(parts) >= MAX_FIELD_DEPTH:
                raise UserError(_("La navegación de campos está limitada a %s niveles.", MAX_FIELD_DEPTH))
            prefix = []
            for part in parts:
                model = self.env[current_model]
                defs = model.fields_get(allfields=[part], attributes=["string", "type", "relation"])
                definition = defs.get(part)
                field = model._fields.get(part)
                relation = getattr(field, "comodel_name", False) if field else False
                if (
                    not field or not definition
                    or field.type not in {"many2one", "one2many", "many2many"}
                    or not relation or not self._model_is_readable(relation)
                ):
                    raise UserError(_("La ruta relacionada '%s' ya no está disponible.", relation_path))
                collection_in_path = collection_in_path or field.type in {"one2many", "many2many"}
                prefix.append(part)
                current_model = relation
                relation_ir = self.env["ir.model"]._get(current_model)
                breadcrumbs.append({
                    "label": definition.get("string") or part,
                    "path": ".".join(prefix),
                    "model": current_model,
                    "model_label": relation_ir.name if relation_ir else current_model,
                })

        model = self.env[current_model]
        field_defs = model.fields_get(attributes=["string", "type", "relation"])
        prefix = f"{relation_path}." if relation_path else ""
        result = []
        for name, definition in field_defs.items():
            field_type = definition.get("type") or ""
            if field_type == "binary" or name.startswith("_"):
                continue
            relation = definition.get("relation") or ""
            is_relational = field_type in {"many2one", "one2many", "many2many"}
            relation_readable = bool(relation and self._model_is_readable(relation)) if is_relational else False
            # A relation whose target cannot be read is omitted entirely.  Even
            # exposing its display_name could otherwise leak restricted data.
            if is_relational and not relation_readable:
                continue
            full_path = prefix + name
            is_collection = collection_in_path or field_type in {"one2many", "many2many"}
            result.append({
                "name": name,
                "path": full_path,
                "label": definition.get("string") or name,
                "type": field_type,
                "relation": relation,
                "navigable": bool(
                    is_relational and relation_readable
                    and len(full_path.split(".")) < MAX_FIELD_DEPTH
                ),
                "is_collection": is_collection,
            })
        result.sort(key=lambda item: (item["label"].casefold(), item["name"]))
        return {
            "fields": result,
            "breadcrumbs": breadcrumbs,
            "relation_path": relation_path,
            "current_model": current_model,
            "current_model_label": (self.env["ir.model"]._get(current_model).name or current_model),
            "depth": len(relation_path.split(".")) if relation_path else 0,
            "collection_in_path": collection_in_path,
        }

    @api.model
    def get_model_fields(self, model_id):
        # Backwards-compatible flat catalog used by older 18.0.2/18.0.3 clients.
        return self.get_field_catalog(model_id, relation_path="")["fields"]

    def _ensure_record_model(self, record):
        self.ensure_one()
        if not record:
            return
        if not self.model_id:
            raise UserError(_("Este diseño no tiene un Modelo de datos configurado."))
        if record._name != self.model_id.model:
            raise UserError(_(
                "El registro %(record_model)s no corresponde al modelo %(template_model)s del diseño.",
                record_model=record._name,
                template_model=self.model_id.model,
            ))
        record.ensure_one()
        record.check_access("read")

    def _format_scalar_value(self, field, value):
        if field.type == "boolean":
            return _("Sí") if value else _("No")
        if value is False or value is None:
            return ""
        if field.type == "selection":
            try:
                labels = dict(field._description_selection(self.env))
                return str(labels.get(value, value))
            except Exception:
                return str(value)
        if field.type == "date":
            return fields.Date.to_string(value)
        if field.type == "datetime":
            return fields.Datetime.to_string(value)
        return str(value)

    def _format_terminal_value(self, field, value):
        if field.type in {"many2one", "one2many", "many2many", "reference"}:
            if not value:
                return []
            if hasattr(value, "check_access"):
                value.check_access("read")
            if hasattr(value, "__iter__") and hasattr(value, "_name"):
                return [record.display_name or "" for record in value]
            return [str(value)]
        return [self._format_scalar_value(field, value)]

    def _resolve_path_values(self, record, path):
        """Resolve a canonical path preserving collection order/cardinality.

        Odoo ``mapped`` unions recordsets and can collapse repeated relational
        records.  Labels often need line-by-line cardinality, so traversal uses
        Python lists and intentionally preserves duplicates across parent rows.
        """
        if not record or not path:
            return [], False
        self._ensure_record_model(record)
        info = self._field_path_info(path)
        current = [record]
        collection_seen = False
        for index, part in enumerate(str(path).split(".")):
            terminal = index == len(str(path).split(".")) - 1
            next_values = []
            for owner in current:
                if not hasattr(owner, "_fields") or part not in owner._fields:
                    continue
                owner.check_access("read")
                field = owner._fields[part]
                # Re-check field visibility in the runtime owner model.
                if part not in owner.fields_get(allfields=[part], attributes=["type"]):
                    continue
                raw = owner[part]
                if terminal:
                    next_values.extend(self._format_terminal_value(field, raw))
                    continue
                if field.type not in {"many2one", "one2many", "many2many"} or not raw:
                    continue
                raw.check_access("read")
                if field.type in {"one2many", "many2many"}:
                    collection_seen = True
                    for related in raw:
                        next_values.append(related)
                        if len(next_values) > MAX_COLLECTION_ITEMS:
                            raise UserError(_(
                                "La ruta '%(path)s' devuelve más de %(max)s registros. "
                                "Use una ruta más específica.", path=path, max=MAX_COLLECTION_ITEMS,
                            ))
                else:
                    next_values.append(raw)
            current = next_values
            if len(current) > MAX_COLLECTION_ITEMS:
                raise UserError(_(
                    "La ruta '%(path)s' devuelve más de %(max)s valores.",
                    path=path, max=MAX_COLLECTION_ITEMS,
                ))
        return current, bool(info["collection"] or collection_seen)

    def _resolve_path(self, record, path, aggregate=None, separator=", "):
        if not record or not path:
            return ""
        values, is_collection = self._resolve_path_values(record, path)
        if not is_collection:
            return str(values[0]) if values else ""

        aggregate = str(aggregate or "").strip().lower()
        if aggregate not in ALLOWED_AGGREGATES:
            raise UserError(_(
                "La ruta '%(path)s' contiene múltiples registros. Seleccione Primero, Último, Unir o Contar.",
                path=path,
            ))
        if aggregate == "count":
            return str(len(values))
        if aggregate == "first":
            return str(values[0]) if values else ""
        if aggregate == "last":
            return str(values[-1]) if values else ""
        separator = str(separator if separator is not None else ", ")
        if len(separator) > 100:
            raise UserError(_("El separador de una colección no puede exceder 100 caracteres."))
        return separator.join(str(value) for value in values if value not in (False, None, ""))

    def _element_value(self, element, record=None):
        source = element.get("source", "static")
        if source == "field":
            if record:
                return self._resolve_path(
                    record,
                    element.get("field_path"),
                    aggregate=element.get("aggregate"),
                    separator=element.get("separator", ", "),
                )
            # Samples exist only for the editor/preview without a business record.
            return str(element.get("sample") or "")
        return str(element.get("value") or "")

    @staticmethod
    def _css_num(value):
        """Return a locale-independent compact CSS number for validated geometry."""
        number = float(value or 0.0)
        text = f"{number:.4f}".rstrip("0").rstrip(".")
        return text or "0"

    def _preview_element_styles(self, element, x_mm, y_mm, w_mm, h_mm):
        """Build preview CSS outside QWeb so report templates never format percent tokens."""
        z_index = int(element.get("z", 0) or 0)
        styles = {
            "container": (
                "position:absolute;"
                f"left:{self._css_num(x_mm)}mm;top:{self._css_num(y_mm)}mm;"
                f"width:{self._css_num(w_mm)}mm;height:{self._css_num(h_mm)}mm;"
                f"overflow:hidden;z-index:{z_index};"
            ),
            "text": "",
            "box": "",
            "line": "",
        }
        etype = element.get("type")
        if etype == "text":
            font_mm = max(0.5, float(element.get("font_mm") or 3))
            alignment = {"L": "left", "C": "center", "R": "right", "J": "justify"}.get(
                element.get("align"), "left"
            )
            styles["text"] = (
                f"font-size:{self._css_num(font_mm)}mm;line-height:1.05;"
                f"text-align:{alignment};white-space:pre-wrap;"
            )
        elif etype == "box":
            thickness = max(0.05, float(element.get("thickness_mm") or 0.25))
            rounding = int(element.get("rounding") or 0) * 2
            styles["box"] = (
                "width:100%;height:100%;box-sizing:border-box;"
                f"border:{self._css_num(thickness)}mm solid #111;border-radius:{rounding}px;"
            )
        elif etype == "line":
            thickness = max(0.05, float(element.get("thickness_mm") or 0.25))
            if element.get("line_direction") == "vertical":
                styles["line"] = (
                    "position:absolute;top:0;bottom:0;left:50%;"
                    f"border-left:{self._css_num(thickness)}mm solid #111;"
                    "transform:translateX(-50%);"
                )
            else:
                styles["line"] = (
                    "position:absolute;left:0;right:0;top:50%;"
                    f"border-top:{self._css_num(thickness)}mm solid #111;"
                    "transform:translateY(-50%);"
                )
        return styles

    def resolve_elements(self, record=None, dpi=None):
        self.ensure_one()
        if record:
            self._ensure_record_model(record)
        target_dpi = int(dpi or self.dpi or 203)
        rendered = []
        preview_types = {"code128": "Code128", "code39": "Standard39", "ean13": "EAN13", "upca": "UPCA"}
        elements = sorted(
            self._parse_design(strict=True, validate_fields=True)["elements"],
            key=lambda element: (int(element.get("z", 0) or 0), str(element.get("id") or "")),
        )
        for element in elements:
            x_mm = float(element.get("x_mm", 0))
            y_mm = float(element.get("y_mm", 0))
            w_mm = float(element.get("w_mm", 1))
            h_mm = float(element.get("h_mm", 1))
            value = self._element_value(element, record=record)
            if len(value) > MAX_RENDERED_CHARS:
                raise UserError(_(
                    "El valor resuelto del elemento '%(element)s' excede el límite de %(limit)s caracteres.",
                    element=element.get("id"), limit=MAX_RENDERED_CHARS,
                ))
            x_dot = round(x_mm * target_dpi / 25.4)
            y_dot = round(y_mm * target_dpi / 25.4)
            w_dot = max(1, round(w_mm * target_dpi / 25.4))
            h_dot = max(1, round(h_mm * target_dpi / 25.4))
            preview_src = False
            if element["type"] in {"barcode", "qrcode"} and value:
                preview_value = value
                if element["type"] == "barcode":
                    kind = element.get("barcode_type", "code128")
                    try:
                        preview_value = self.env["ickab.label.renderer.zpl"]._validate_barcode(kind, value)
                    except UserError:
                        preview_value = ""
                if preview_value:
                    barcode_type = "QR" if element["type"] == "qrcode" else preview_types[element.get("barcode_type", "code128")]
                    params = {
                        "barcode_type": barcode_type,
                        "value": preview_value,
                        "width": max(40, min(2400, w_dot)),
                        "height": max(40, min(2400, h_dot)),
                    }
                    if element["type"] == "barcode" and element.get("human_readable", True):
                        params["humanreadable"] = 1
                    preview_src = "/report/barcode/?" + urlencode(params)
            preview_styles = self._preview_element_styles(element, x_mm, y_mm, w_mm, h_mm)
            rendered.append({
                **element,
                "value_resolved": value,
                "preview_src": preview_src,
                "preview_container_style": preview_styles["container"],
                "preview_text_style": preview_styles["text"],
                "preview_box_style": preview_styles["box"],
                "preview_line_style": preview_styles["line"],
                "x_dot": x_dot,
                "y_dot": y_dot,
                "w_dot": w_dot,
                "h_dot": h_dot,
                "x_pct": (x_mm / self.width_mm) * 100.0,
                "y_pct": (y_mm / self.height_mm) * 100.0,
                "w_pct": (w_mm / self.width_mm) * 100.0,
                "h_pct": (h_mm / self.height_mm) * 100.0,
            })
        return rendered

    def get_physical_profile(self):
        """Neutral physical-label contract consumed by Studio and optional agents."""
        self.ensure_one()
        is_continuous = self.media_type == "continuous"
        return {
            "schema": "ickab.label.media/1",
            "technical_key": self.technical_key,
            "shape": self.shape,
            "width_mm": float(self.width_mm),
            "height_mm": float(self.height_mm),
            "dpi_reference": int(self.dpi or 203),
            "dpi": int(self.dpi or 203),  # compatibility alias for existing print bridges
            "media_type": self.media_type,
            "gap_mm": 0.0 if is_continuous else float(self.gap_mm or 0.0),
            "gap_offset_mm": 0.0 if is_continuous else float(self.gap_offset_mm or 0.0),
            "safe_margin_mm": float(self.safe_margin_mm or 0.0),
            "bleed_mm": float(self.bleed_mm or 0.0),
            "orientation": "landscape" if self.width_mm >= self.height_mm else "portrait",
            "company_id": self.company_id.id or False,
        }

    def build_print_document(self, record=None, copies=1):
        """Return the printer-neutral document owned by Label Studio.

        Print agents/renderers may consume this contract without learning how the
        visual editor stores its state. This is the canonical hand-off boundary.
        """
        self.ensure_one()
        copies = max(1, int(copies or 1))
        if self.document_mode == "zpl_raw":
            return {
                "schema": "ickab.label.document/1",
                "template_key": self.technical_key,
                "mode": "raw",
                "raw_language": "zpl",
                "raw_content": self.source_zpl or "",
                "media": self.get_physical_profile(),
                "copies": copies,
                "elements": self.resolve_elements(record=None),
            }
        return {
            "schema": "ickab.label.document/1",
            "template_key": self.technical_key,
            "mode": "studio",
            "media": self.get_physical_profile(),
            "copies": copies,
            "model": self.model_id.model if self.model_id else False,
            "record_id": record.id if record else False,
            "elements": [
                {
                    "id": el["id"],
                    "type": el["type"],
                    "x_mm": float(el["x_mm"]),
                    "y_mm": float(el["y_mm"]),
                    "w_mm": float(el["w_mm"]),
                    "h_mm": float(el["h_mm"]),
                    "z": int(el.get("z", 0) or 0),
                    "value": el.get("value_resolved", ""),
                    **{key: el[key] for key in (
                        "font_mm", "align", "max_lines", "barcode_type", "human_readable",
                        "magnification", "thickness_mm", "line_direction", "rounding"
                    ) if key in el},
                }
                for el in self.resolve_elements(record=record)
            ],
        }

    def _label_renderer_registry(self):
        """Extension point. Studio owns design; renderers/agents own output languages."""
        return {"zpl": "ickab.label.renderer.zpl"}

    def render_payload(self, record=None, dpi=None, copies=1, language="zpl"):
        self.ensure_one()
        language = str(language or "zpl").lower()
        if self.document_mode == "zpl_raw":
            if language != "zpl":
                raise UserError(_("Un diseño ZPL RAW sólo puede exportarse como ZPL."))
            content = self.source_zpl or ""
            copies = max(1, int(copies or 1))
            if copies > 1:
                content = (content.rstrip() + "\n") * copies
            return {
                "language": "zpl",
                "content": content,
                "content_type": "application/octet-stream",
                "extension": "zpl",
                "dpi": int(dpi or self.zpl_source_dpi or self.dpi or 203),
                "width_mm": self.width_mm,
                "height_mm": self.height_mm,
                "copies": copies,
                "template_key": self.technical_key,
                "profile": self.get_physical_profile(),
                "document": self.build_print_document(record=None, copies=copies),
            }
        renderer_model = self._label_renderer_registry().get(language)
        if not renderer_model:
            raise UserError(_("El motor '%s' no está disponible en esta instalación.", language))
        payload = self.env[renderer_model].render(self, record=record, dpi=dpi, copies=copies)
        payload.update({
            "template_key": self.technical_key,
            "profile": self.get_physical_profile(),
            "document": self.build_print_document(record=record, copies=copies),
        })
        return payload

    def render_batch(self, records_with_qty=None, dpi=None, language="zpl"):
        self.ensure_one()
        records_with_qty = records_with_qty or [(False, 1)]
        target_dpi = int(dpi or self.dpi or 203)
        if self.document_mode == "zpl_raw":
            total = sum(max(0, int(qty or 0)) for _record, qty in records_with_qty) or 1
            payload = self.render_payload(record=None, dpi=target_dpi, copies=total, language="zpl")
            payload["labels_count"] = total
            return payload
        contents = []
        for record, qty in records_with_qty:
            qty = int(qty or 0)
            if qty <= 0:
                continue
            payload = self.render_payload(record=record, dpi=target_dpi, copies=qty, language=language)
            contents.append(payload["content"])
        total_labels = sum(max(0, int(qty or 0)) for _record, qty in records_with_qty)
        return {
            "language": language,
            "content": "\n".join(contents) + ("\n" if contents else ""),
            "content_type": "application/octet-stream",
            "extension": "zpl" if language == "zpl" else "txt",
            "dpi": target_dpi,
            "width_mm": self.width_mm,
            "height_mm": self.height_mm,
            "labels_count": total_labels,
            "template_key": self.technical_key,
            "profile": self.get_physical_profile(),
        }

    def generate_zpl(self, record=None, dpi=None, copies=1):
        return self.render_payload(record=record, dpi=dpi, copies=copies, language="zpl")["content"]

    def get_preview_pages(self, records_with_qty=None):
        self.ensure_one()
        records_with_qty = records_with_qty or [(False, 1)]
        requested = sum(max(0, int(qty or 0)) for _record, qty in records_with_qty)
        if requested > MAX_PREVIEW_LABELS:
            raise UserError(_(
                "La vista previa está limitada a %(max)s etiquetas por operación. "
                "La impresión/descarga puede conservar la cantidad completa.",
                max=MAX_PREVIEW_LABELS,
            ))
        pages = []
        for record, qty in records_with_qty:
            for _copy in range(max(0, int(qty or 0))):
                radius = "50%" if self.shape in {"circle", "oval"} else "0"
                safe = self._css_num(self.safe_margin_mm)
                pages.append({
                    "template": self,
                    "record": record,
                    "elements": self.resolve_elements(record=record if self.document_mode == "studio" else None),
                    "width_mm": self.width_mm,
                    "height_mm": self.height_mm,
                    "shape": self.shape,
                    "safe_margin_mm": self.safe_margin_mm,
                    "page_style": (
                        "position:relative;background:white;border:1px solid #777;overflow:hidden;"
                        f"width:{self._css_num(self.width_mm)}mm;height:{self._css_num(self.height_mm)}mm;"
                        f"border-radius:{radius};"
                    ),
                    "safe_style": (
                        "position:absolute;pointer-events:none;border:1px dashed #bbb;"
                        f"left:{safe}mm;top:{safe}mm;right:{safe}mm;bottom:{safe}mm;"
                        f"border-radius:{radius};"
                    ),
                    "raw_mode": self.document_mode == "zpl_raw",
                })
        return pages

    def action_preview(self):
        self.ensure_one()
        return self.env.ref("ickab_label_studio.action_report_label_preview").report_action(
            self, data={"template_id": self.id}, config=False
        )

    def action_download_zpl(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_url",
            "url": f"/ickab_label_studio/zpl/template/{self.id}",
            "target": "self",
        }

    def action_open_import_zpl(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": _("Importar ZPL"),
            "res_model": "ickab.label.zpl.import.wizard",
            "view_mode": "form",
            "target": "new",
            "context": {
                "default_target_template_id": self.id,
                "default_template_name": self.name,
                "default_model_id": self.model_id.id if self.model_id else False,
                "default_source_dpi": self.dpi,
                "default_source_zpl": self.source_zpl or "",
            },
        }

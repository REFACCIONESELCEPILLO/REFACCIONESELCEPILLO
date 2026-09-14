from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class IckabPrintPaper(models.Model):
    _name = "ickab.print.paper"
    _description = "ICKAB Print Paper"
    _order = "category, width_mm, height_mm, name"

    name = fields.Char(required=True)
    code = fields.Char(required=True, index=True)
    company_id = fields.Many2one(
        "res.company",
        string="Compañía",
        help="Déjalo vacío para que el tipo de papel esté disponible para todas las compañías.",
    )
    active = fields.Boolean(default=True)
    category = fields.Selection(
        [("label", "Etiqueta"), ("ticket", "Ticket"), ("document", "Documento")],
        required=True,
        index=True,
    )
    width_mm = fields.Float(string="Ancho (mm)", required=True, digits=(8, 2))
    height_mm = fields.Float(
        string="Alto (mm)",
        digits=(8, 2),
        help="En tickets de longitud variable puede dejarse en 0.",
    )
    orientation = fields.Selection(
        [("portrait", "Vertical"), ("landscape", "Horizontal")],
        default="portrait",
        required=True,
    )
    sensor_mode = fields.Selection(
        [("gap", "Separación / GAP"), ("blackmark", "Marca negra / BLINE"), ("continuous", "Continuo")],
        string="Sensor de medio",
        default="gap",
        required=True,
    )
    gap_mm = fields.Float(
        string="Separación (mm)",
        default=2.0,
        digits=(8, 2),
        help="Separación física entre etiquetas. Es una propiedad del consumible, no de la impresora.",
    )
    gap_offset_mm = fields.Float(
        string="Offset de separación (mm)",
        default=0.0,
        digits=(8, 2),
    )
    default_dpi = fields.Selection(
        [("203", "203 dpi"), ("300", "300 dpi"), ("600", "600 dpi"), ("na", "No aplica")],
        default="na",
        string="DPI predeterminado",
    )
    size_description = fields.Char(compute="_compute_size_description", string="Medida")

    _sql_constraints = [
        ("code_company_unique", "unique(code, company_id)", "El código de papel debe ser único por compañía."),
    ]

    @api.depends("width_mm", "height_mm", "category")
    def _compute_size_description(self):
        for paper in self:
            if paper.category == "ticket" and not paper.height_mm:
                paper.size_description = _("%s mm × variable") % (paper.width_mm or 0)
            else:
                paper.size_description = _("%s × %s mm") % (paper.width_mm or 0, paper.height_mm or 0)

    @api.constrains("width_mm", "height_mm", "category", "gap_mm")
    def _check_dimensions(self):
        for paper in self:
            if paper.width_mm <= 0:
                raise ValidationError(_("El ancho del papel debe ser mayor a cero."))
            if paper.category != "ticket" and paper.height_mm <= 0:
                raise ValidationError(_("Las etiquetas y documentos requieren una altura mayor a cero."))
            if paper.height_mm < 0:
                raise ValidationError(_("La altura no puede ser negativa."))
            if paper.gap_mm < 0:
                raise ValidationError(_("La separación entre etiquetas no puede ser negativa."))

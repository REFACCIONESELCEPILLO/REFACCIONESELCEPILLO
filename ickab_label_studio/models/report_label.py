# Copyright 2026 ICKAB. All rights reserved.
from odoo import _, api, models
from odoo.exceptions import UserError


class LabelPreviewReport(models.AbstractModel):
    _name = "report.ickab_label_studio.report_label_preview"
    _description = "ICKAB Label Studio Preview"

    @api.model
    def _get_report_values(self, docids, data=None):
        data = data or {}
        template_id = data.get("template_id") or (docids[0] if docids else 0)
        try:
            template_id = int(template_id or 0)
        except (TypeError, ValueError):
            template_id = 0
        template = self.env["ickab.label.template"].browse(template_id).exists()
        if not template:
            raise UserError(_("No se encontró el diseño de etiqueta."))
        template.check_access("read")
        report_service = self.env["ir.actions.report"]
        records_with_qty = report_service._label_studio_records_with_qty(template, data=data)
        if (data.get("quantity_by_record") or {}) and not records_with_qty:
            raise UserError(_("No hay registros válidos para previsualizar."))
        pages = template.get_preview_pages(records_with_qty or [(False, 1)])
        return {"docs": template, "pages": pages}

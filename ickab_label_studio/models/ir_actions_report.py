# Copyright 2026 ICKAB. All rights reserved.
from odoo import _, api, models
from odoo.exceptions import UserError


class IrActionsReportLabelStudio(models.Model):
    _inherit = "ir.actions.report"

    _LABEL_STUDIO_REPORT = "ickab_label_studio.report_label_zpl"

    def _label_studio_template(self, res_ids=None, data=None):
        data = data or {}
        template_id = data.get("template_id")
        if not template_id:
            if isinstance(res_ids, int):
                res_ids = [res_ids]
            if res_ids:
                template_id = res_ids[0]
        try:
            template_id = int(template_id or 0)
        except (TypeError, ValueError):
            template_id = 0
        return self.env["ickab.label.template"].browse(template_id).exists()

    def _label_studio_records_with_qty(self, template, data=None):
        data = data or {}
        template_model = template.model_id.model if template.model_id else False
        model_name = data.get("active_model") or template_model
        quantities = data.get("quantity_by_record") or {}
        if quantities and not template_model:
            raise UserError(_("El diseño no tiene un Modelo de datos configurado para resolver registros."))
        if model_name and template_model and model_name != template_model:
            raise UserError(_("Los registros no corresponden al modelo configurado en el diseño."))
        result = []
        for record_id, qty in quantities.items():
            try:
                record_id = int(record_id)
                qty = int(qty or 0)
            except (TypeError, ValueError):
                continue
            if qty <= 0:
                continue
            if not model_name:
                continue
            record = self.env[model_name].browse(record_id).exists()
            if record:
                record.check_access("read")
                result.append((record, qty))
        return result

    def _label_studio_render_data(self, template, data=None, dpi=None):
        data = data or {}
        records_with_qty = self._label_studio_records_with_qty(template, data=data)
        if (data.get("quantity_by_record") or {}) and not records_with_qty:
            raise UserError(_("No hay registros válidos con cantidad positiva para generar etiquetas."))
        return template.render_batch(records_with_qty or [(False, 1)], dpi=dpi, language="zpl")

    @api.model
    def _render_qweb_text(self, report_ref, res_ids, data=None):
        report = self._get_report(report_ref)
        if report.report_name != self._LABEL_STUDIO_REPORT:
            return super()._render_qweb_text(report_ref, res_ids, data=data)
        template = self._label_studio_template(res_ids=res_ids, data=data)
        if not template:
            raise UserError(_("No se encontró el diseño de etiqueta."))
        template.check_access("read")
        payload = self._label_studio_render_data(template, data=data, dpi=(data or {}).get("label_dpi"))
        return payload["content"].encode("utf-8"), "text"

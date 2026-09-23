# Copyright 2026 ICKAB. All rights reserved.
"""Integration between ICKAB Label Studio and ICKAB Direct Print.

Label Studio owns design and preview.  Printing always goes through Direct Print,
which owns printer selection, capabilities, language/rendering, queueing and Print
Agent delivery.  Export/import actions remain design utilities and are not an
alternate physical print path.
"""

import logging

from odoo import _, api, fields, models
from odoo.exceptions import UserError


_logger = logging.getLogger(__name__)

MANAGED_PAPER_PREFIX = "LABEL_STUDIO_"
PAPER_TOLERANCE_MM = 0.01
DIRECT_PRINT_GROUP = "ickab_direct_print.group_direct_print_user"
DIRECT_PRINT_PAPER_MODEL = "ickab.print.paper"
DIRECT_PRINT_REQUIRED_PAPER_FIELDS = {
    "name",
    "code",
    "active",
    "category",
    "width_mm",
    "height_mm",
    "orientation",
    "default_dpi",
    "sensor_mode",
    "gap_mm",
    "gap_offset_mm",
}
DIRECT_PRINT_REPORT_VALUES = {
    "ickab_print_mode": "ask",
    "ickab_document_kind": "label",
    "ickab_text_language": "auto",
    "ickab_copies": 1,
    "ickab_fallback_download": False,
}


class IckabLabelTemplateDirectPrintIntegration(models.Model):
    _inherit = "ickab.label.template"

    direct_print_available = fields.Boolean(
        string="Direct Print disponible",
        compute="_compute_direct_print_available",
        help="Se activa automáticamente cuando ICKAB Direct Print está instalado y el usuario tiene permiso de impresión.",
    )

    @api.depends_context("uid")
    def _compute_direct_print_available(self):
        available = self._direct_print_runtime_available() and self._direct_print_user_allowed()
        for record in self:
            record.direct_print_available = available

    @api.model
    def _direct_print_runtime_available(self):
        """Return True when the required Direct Print runtime is loaded."""
        return DIRECT_PRINT_PAPER_MODEL in self.env.registry.models

    @api.model
    def _direct_print_user_allowed(self):
        group = self.env.ref(DIRECT_PRINT_GROUP, raise_if_not_found=False)
        if not group:
            return False
        return self.env.user.has_group(DIRECT_PRINT_GROUP)

    def _direct_print_assert_available(self):
        self.ensure_one()
        if not self._direct_print_runtime_available():
            raise UserError(_(
                "ICKAB Direct Print no está instalado o no está cargado en esta base de datos. "
                "La impresión física desde Label Studio requiere ICKAB Direct Print."
            ))
        if not self._direct_print_user_allowed():
            raise UserError(_("No tiene permisos para utilizar ICKAB Direct Print."))
        return True

    def _direct_print_managed_paper_code(self):
        self.ensure_one()
        return f"{MANAGED_PAPER_PREFIX}{self.technical_key.upper()}"

    @staticmethod
    def _direct_print_is_managed_paper(paper):
        return bool(paper and (paper.code or "").startswith(MANAGED_PAPER_PREFIX))

    def _direct_print_check_paper_contract(self):
        self.ensure_one()
        self._direct_print_assert_available()
        Paper = self.env[DIRECT_PRINT_PAPER_MODEL]
        missing = sorted(DIRECT_PRINT_REQUIRED_PAPER_FIELDS - set(Paper._fields))
        if missing:
            raise UserError(_(
                "La versión instalada de ICKAB Direct Print no cumple el contrato de formatos requerido por Label Studio. "
                "Faltan los campos: %(fields)s",
                fields=", ".join(missing),
            ))
        return Paper

    def _direct_print_paper_matches(self, paper):
        self.ensure_one()
        if not paper:
            return False
        profile = self.get_physical_profile()
        if paper.category != "label":
            return False
        if abs((paper.width_mm or 0.0) - profile["width_mm"]) > PAPER_TOLERANCE_MM:
            return False
        if abs((paper.height_mm or 0.0) - profile["height_mm"]) > PAPER_TOLERANCE_MM:
            return False
        if (paper.sensor_mode or "gap") != profile["media_type"]:
            return False
        if profile["media_type"] != "continuous":
            if abs((paper.gap_mm or 0.0) - profile["gap_mm"]) > PAPER_TOLERANCE_MM:
                return False
            if abs((paper.gap_offset_mm or 0.0) - profile["gap_offset_mm"]) > PAPER_TOLERANCE_MM:
                return False
        if "company_id" in paper._fields and paper.company_id and paper.company_id != self.company_id:
            return False
        return True

    def _direct_print_paper_values(self):
        self.ensure_one()
        profile = self.get_physical_profile()
        values = {
            "name": _("Label Studio: %(name)s", name=self.name),
            "code": self._direct_print_managed_paper_code(),
            "active": True,
            "category": "label",
            "width_mm": profile["width_mm"],
            "height_mm": profile["height_mm"],
            "orientation": profile["orientation"],
            "default_dpi": str(profile["dpi"]),
            "sensor_mode": profile["media_type"],
            "gap_mm": profile["gap_mm"],
            "gap_offset_mm": profile["gap_offset_mm"],
        }
        Paper = self.env[DIRECT_PRINT_PAPER_MODEL]
        if "company_id" in Paper._fields:
            values["company_id"] = profile["company_id"]
        return values

    def _direct_print_paper_code(self):
        """Return/create a Direct Print media code lazily at print time.

        Saving a Studio design never calls Direct Print. This keeps design work
        independent from printer infrastructure while still letting Direct Print
        receive the physical paper profile when the user actually prints.
        """
        self.ensure_one()
        PaperModel = self._direct_print_check_paper_contract()
        Paper = PaperModel.sudo().with_context(active_test=False)
        profile = self.get_physical_profile()

        domain = [("active", "=", True), ("category", "=", "label")]
        if "company_id" in PaperModel._fields:
            domain.extend(["|", ("company_id", "=", False), ("company_id", "=", self.company_id.id)])

        candidates = Paper.search(domain)
        shared = candidates.filtered(
            lambda paper: bool(paper.code)
            and not self._direct_print_is_managed_paper(paper)
            and self._direct_print_paper_matches(paper)
        )[:1]
        if shared:
            return shared.code

        values = self._direct_print_paper_values()
        managed = Paper.search([("code", "=", values["code"])], limit=1)
        if managed:
            managed.write(values)
        else:
            managed = Paper.create(values)
        return managed.code

    def _direct_print_configure_report(self, report):
        """Activate Direct Print's existing AUTO-language contract on the report."""
        self.ensure_one()
        self._direct_print_assert_available()
        missing = sorted(set(DIRECT_PRINT_REPORT_VALUES) - set(report._fields))
        if missing:
            raise UserError(_(
                "La versión instalada de ICKAB Direct Print no cumple el contrato de reportes requerido por Label Studio. "
                "Faltan los campos: %(fields)s",
                fields=", ".join(missing),
            ))
        values = {
            field_name: value
            for field_name, value in DIRECT_PRINT_REPORT_VALUES.items()
            if report[field_name] != value
        }
        if values:
            report.sudo().write(values)
        return report

    def _direct_print_prepare_data(self, data=None):
        """Enrich report data without choosing a printer language.

        ``ickab_text_language`` remains ``auto``. Studio never inspects
        ``printer.language`` and never decides ZPL/TSPL; Direct Print does.
        """
        self.ensure_one()
        self._direct_print_assert_available()
        result = dict(data or {})
        result.setdefault("template_id", self.id)
        result.setdefault("label_dpi", int(self.dpi or 203))
        result["ickab_paper_code"] = self._direct_print_paper_code()
        result.setdefault("ickab_label_studio_mode", self.document_mode)
        result.setdefault("ickab_label_studio_template_key", self.technical_key)
        return result

    def action_direct_print(self):
        """Hand the completed Studio design to ICKAB Direct Print."""
        self.ensure_one()
        self.check_access("read")
        self._direct_print_assert_available()
        report = self.env.ref("ickab_label_studio.action_report_label_zpl")
        self._direct_print_configure_report(report)
        data = self._direct_print_prepare_data({
            "template_id": self.id,
            "label_dpi": int(self.dpi or 203),
        })
        # Direct Print owns the flow from here: printer selection, language AUTO,
        # queue/job creation and delivery through ICKAB Print Agent.
        return report.report_action(self, data=data, config=False)

    def unlink(self):
        """Archive managed paper records when possible, never blocking Studio."""
        codes = [
            f"{MANAGED_PAPER_PREFIX}{record.technical_key.upper()}"
            for record in self
            if record.technical_key
        ]
        result = super().unlink()
        if codes and self._direct_print_runtime_available():
            try:
                Paper = self.env[DIRECT_PRINT_PAPER_MODEL].sudo().with_context(active_test=False)
                Paper.search([("code", "in", codes)]).write({"active": False})
            except Exception:  # pragma: no cover - cleanup must never block Studio
                _logger.warning("Could not archive Label Studio managed Direct Print papers", exc_info=True)
        return result

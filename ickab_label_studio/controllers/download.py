# Copyright 2026 ICKAB. All rights reserved.
import re

from odoo import http
from odoo.http import content_disposition, request
from werkzeug.exceptions import NotFound


class IckabLabelStudioDownloadController(http.Controller):
    @staticmethod
    def _safe_filename(value):
        value = re.sub(r"[^A-Za-z0-9._-]+", "_", str(value or "label")).strip("._")
        return (value or "label")[:120]

    @classmethod
    def _zpl_response(cls, filename, content):
        filename = cls._safe_filename(filename.rsplit(".", 1)[0]) + ".zpl"
        body = content.encode("utf-8")
        return request.make_response(body, headers=[
            ("Content-Type", "application/octet-stream"),
            ("Content-Length", str(len(body))),
            ("Content-Disposition", content_disposition(filename)),
            ("X-Content-Type-Options", "nosniff"),
        ])

    @http.route("/ickab_label_studio/zpl/template/<int:template_id>", type="http", auth="user", methods=["GET"])
    def download_template_zpl(self, template_id, **kwargs):
        template = request.env["ickab.label.template"].browse(template_id).exists()
        if not template:
            raise NotFound()
        template.check_access("read")
        payload = template.render_batch([(False, 1)], language="zpl")
        return self._zpl_response(f"{template.name or 'label'}.zpl", payload["content"])

    @http.route("/ickab_label_studio/zpl/product_layout/<int:wizard_id>", type="http", auth="user", methods=["GET"])
    def download_product_layout_zpl(self, wizard_id, **kwargs):
        wizard = request.env["product.label.layout"].browse(wizard_id).exists()
        if not wizard:
            raise NotFound()
        wizard.check_access("read")
        data = wizard._ickab_studio_prepare_data()
        template = request.env["ickab.label.template"].browse(data["template_id"]).exists()
        if not template:
            raise NotFound()
        template.check_access("read")
        payload = request.env["ir.actions.report"]._label_studio_render_data(template, data=data, dpi=data.get("label_dpi"))
        return self._zpl_response(f"{template.name or 'labels'}.zpl", payload["content"])

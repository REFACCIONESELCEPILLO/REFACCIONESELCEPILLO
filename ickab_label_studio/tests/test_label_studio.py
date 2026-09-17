import base64
import json

from PIL import Image

from odoo.exceptions import UserError, ValidationError
from odoo.tests import tagged
from odoo.tests.common import TransactionCase


@tagged("post_install", "-at_install")
class TestIckabLabelStudio(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.model = cls.env["ir.model"]._get("product.product")
        cls.product = cls.env["product.product"].create({
            "name": "Producto prueba ICKAB",
            "default_code": "ICK-001",
            "barcode": "7501234567890",
        })

    def _design_v2(self):
        return {
            "version": 2,
            "elements": [
                {
                    "id": "sku", "type": "text", "x_mm": 2.5, "y_mm": 1.5,
                    "w_mm": 45, "h_mm": 5, "z": 1, "source": "field",
                    "field_path": "default_code", "sample": "MUESTRA", "font_mm": 3,
                    "align": "L", "max_lines": 1,
                },
                {
                    "id": "bar", "type": "barcode", "x_mm": 2.5, "y_mm": 9,
                    "w_mm": 45, "h_mm": 13.5, "z": 2, "source": "field",
                    "field_path": "barcode", "barcode_type": "code128", "human_readable": True,
                },
            ],
        }

    def _template(self, design=None, **extra):
        vals = {
            "name": "Prueba 50x30",
            "model_id": self.model.id,
            "width_mm": 50,
            "height_mm": 30,
            "dpi": "203",
            "design_json": json.dumps(design or self._design_v2()),
        }
        vals.update(extra)
        return self.env["ickab.label.template"].create(vals)

    def test_v2_geometry_is_physical(self):
        template = self._template()
        elements = template.resolve_elements(self.product)
        self.assertEqual(elements[0]["x_mm"], 2.5)
        self.assertEqual(elements[0]["x_dot"], round(2.5 * 203 / 25.4))
        self.assertAlmostEqual(elements[0]["x_pct"], 5.0)

    def test_zpl_uses_physical_size_and_record(self):
        template = self._template()
        zpl = template.generate_zpl(self.product)
        self.assertIn("^PW400", zpl)
        self.assertIn("^LL240", zpl)
        self.assertIn("ICK-001", zpl)
        self.assertIn("7501234567890", zpl)
        self.assertIn("^BCN", zpl)

    def test_v1_design_remains_backward_compatible(self):
        legacy = {
            "version": 1,
            "elements": [{
                "id": "legacy", "type": "text", "x": 10, "y": 20, "w": 50, "h": 10,
                "source": "static", "value": "LEGACY", "font_mm": 3, "max_lines": 1,
            }],
        }
        template = self._template(legacy)
        parsed = template._parse_design(strict=True)
        self.assertEqual(parsed["version"], 2)
        self.assertAlmostEqual(parsed["elements"][0]["x_mm"], 5.0)
        self.assertAlmostEqual(parsed["elements"][0]["y_mm"], 6.0)

    def test_empty_real_field_does_not_print_sample(self):
        template = self._template()
        self.product.default_code = False
        values = [e["value_resolved"] for e in template.resolve_elements(self.product)]
        self.assertEqual(values[0], "")
        self.assertNotIn("MUESTRA", template.generate_zpl(self.product))

    def test_sample_is_used_only_without_business_record(self):
        template = self._template()
        values = [e["value_resolved"] for e in template.resolve_elements()]
        self.assertEqual(values[0], "MUESTRA")

    def test_record_model_must_match_template(self):
        template = self._template()
        with self.assertRaises(UserError):
            template.generate_zpl(self.product.product_tmpl_id)

    def test_static_design_can_have_no_model(self):
        design = {"version": 2, "elements": [{
            "id": "static", "type": "text", "x_mm": 1, "y_mm": 1, "w_mm": 20, "h_mm": 5,
            "source": "static", "value": "STATIC", "font_mm": 3, "max_lines": 1,
        }]}
        template = self.env["ickab.label.template"].create({
            "name": "Estática", "width_mm": 30, "height_mm": 20, "design_json": json.dumps(design),
        })
        self.assertIn("STATIC", template.generate_zpl())

    def test_dynamic_field_requires_model(self):
        design = {"version": 2, "elements": [{
            "id": "dynamic", "type": "text", "x_mm": 1, "y_mm": 1, "w_mm": 20, "h_mm": 5,
            "source": "field", "field_path": "name", "sample": "X", "font_mm": 3, "max_lines": 1,
        }]}
        with self.assertRaises(ValidationError):
            self.env["ickab.label.template"].create({
                "name": "Inválida", "width_mm": 30, "height_mm": 20, "design_json": json.dumps(design),
            })

    def test_element_must_fit_inside_label(self):
        design = {"version": 2, "elements": [{
            "id": "bad", "type": "text", "x_mm": 45, "y_mm": 0, "w_mm": 10, "h_mm": 5,
            "source": "static", "value": "X", "font_mm": 3, "max_lines": 1,
        }]}
        with self.assertRaises(ValidationError):
            self._template(design)

    def test_batch_uses_native_copy_count(self):
        template = self._template()
        payload = template.render_batch([(self.product, 3)])
        self.assertEqual(payload["content"].count("^XA"), 1)
        self.assertIn("^PQ3,0,1,N", payload["content"])

    def test_neutral_print_document_contains_mm_geometry(self):
        template = self._template()
        doc = template.build_print_document(self.product, copies=2)
        self.assertEqual(doc["schema"], "ickab.label.document/1")
        self.assertEqual(doc["mode"], "studio")
        self.assertEqual(doc["media"]["width_mm"], 50.0)
        self.assertEqual(doc["elements"][0]["x_mm"], 2.5)
        self.assertEqual(doc["copies"], 2)

    def test_core_has_no_direct_print_model_dependency(self):
        template = self._template()
        self.assertNotIn("ickab_paper_id", template._fields)

    def test_zpl_parser_imports_common_objects(self):
        zpl = """^XA^PW400^LL240^FO20,20^A0N,30,30^FDHELLO^FS^FO20,80^BCN,70,Y,N,N^FD123456^FS^XZ"""
        parsed = self.env["ickab.label.zpl.parser"].parse(zpl, dpi=203)
        self.assertTrue(parsed["fully_editable"])
        self.assertAlmostEqual(parsed["width_mm"], 400 * 25.4 / 203, places=3)
        self.assertEqual(parsed["design"]["elements"][0]["type"], "text")
        self.assertEqual(parsed["design"]["elements"][1]["type"], "barcode")

    def test_zpl_parser_marks_unknown_commands(self):
        parsed = self.env["ickab.label.zpl.parser"].parse("^XA^PW400^LL240^FO20,20^XGLOGO.GRF,1,1^FS^XZ", dpi=203)
        self.assertFalse(parsed["fully_editable"])
        self.assertIn("^XG", parsed["unsupported"])

    def test_raw_zpl_is_preserved(self):
        raw = "^XA\n^PW400\n^LL240\n^FO10,10^FDRAW^FS\n^XZ"
        template = self._template(
            {"version": 2, "elements": []},
            document_mode="zpl_raw",
            source_zpl=raw,
            zpl_source_dpi="203",
        )
        self.assertEqual(template.generate_zpl(), raw)
        doc = template.build_print_document()
        self.assertEqual(doc["mode"], "raw")
        self.assertEqual(doc["raw_content"], raw)

    def test_circle_requires_equal_sides(self):
        with self.assertRaises(ValidationError):
            self._template(shape="circle", width_mm=40, height_mm=30)

    def test_media_presets_are_available(self):
        media = self.env.ref("ickab_label_studio.media_shipping_4x6")
        self.assertEqual(media.category, "shipping")
        self.assertAlmostEqual(media.width_mm, 101.6)
        self.assertAlmostEqual(media.height_mm, 152.4)

    def test_model_field_catalog_contains_product_fields(self):
        fields_catalog = self.env["ickab.label.template"].get_model_fields(self.model.id)
        names = {item["name"] for item in fields_catalog}
        self.assertIn("name", names)
        self.assertIn("default_code", names)
        self.assertIn("barcode", names)

    def test_preview_qweb_renders_percent_css_without_format_error(self):
        design = {
            "version": 2,
            "elements": [
                {
                    "id": "txt", "type": "text", "x_mm": 2, "y_mm": 2,
                    "w_mm": 20, "h_mm": 5, "z": 1, "source": "static",
                    "value": "PREVIEW", "font_mm": 3, "align": "C", "max_lines": 1,
                },
                {
                    "id": "box", "type": "box", "x_mm": 1, "y_mm": 10,
                    "w_mm": 30, "h_mm": 12, "z": 2, "thickness_mm": 0.25,
                    "rounding": 2,
                },
                {
                    "id": "line", "type": "line", "x_mm": 5, "y_mm": 25,
                    "w_mm": 25, "h_mm": 2, "z": 3, "thickness_mm": 0.25,
                    "line_direction": "horizontal",
                },
            ],
        }
        template = self._template(
            design, shape="circle", width_mm=40, height_mm=40, safe_margin_mm=1.5
        )
        report_model = self.env["report.ickab_label_studio.report_label_preview"]
        values = report_model._get_report_values(
            [template.id], data={"template_id": template.id}
        )
        html = self.env["ir.ui.view"]._render_template(
            "ickab_label_studio.report_label_preview", values
        )
        html = html.decode() if isinstance(html, bytes) else str(html)
        self.assertIn("border-radius:50%", html)
        self.assertIn("left:1.5mm", html)
        self.assertIn("width:100%", html)
        self.assertIn("top:50%", html)

    def test_new_small_template_starts_empty_and_valid(self):
        template = self.env["ickab.label.template"].create({
            "name": "Circular pequeña",
            "shape": "circle",
            "width_mm": 20,
            "height_mm": 20,
        })
        self.assertEqual(template.element_count, 0)
        self.assertEqual(template._parse_design(strict=True)["elements"], [])

    def test_related_many2one_path_resolves(self):
        design = {"version": 2, "elements": [{
            "id": "category", "type": "text", "x_mm": 1, "y_mm": 1,
            "w_mm": 40, "h_mm": 5, "source": "field",
            "field_path": "product_tmpl_id.categ_id.name", "font_mm": 3,
            "max_lines": 1,
        }]}
        template = self._template(design)
        value = template.resolve_elements(self.product)[0]["value_resolved"]
        self.assertEqual(value, self.product.categ_id.name)

    def test_relational_catalog_navigates_and_returns_canonical_paths(self):
        root = self.env["ickab.label.template"].get_field_catalog(self.model.id, "")
        product_tmpl = next(field for field in root["fields"] if field["name"] == "product_tmpl_id")
        self.assertTrue(product_tmpl["navigable"])
        self.assertEqual(product_tmpl["path"], "product_tmpl_id")
        nested = self.env["ickab.label.template"].get_field_catalog(self.model.id, "product_tmpl_id")
        category = next(field for field in nested["fields"] if field["name"] == "categ_id")
        self.assertEqual(category["path"], "product_tmpl_id.categ_id")
        self.assertEqual(nested["breadcrumbs"][-1]["path"], "product_tmpl_id")

    def test_collection_path_requires_explicit_aggregate(self):
        design = {"version": 2, "elements": [{
            "id": "variants", "type": "text", "x_mm": 1, "y_mm": 1,
            "w_mm": 40, "h_mm": 5, "source": "field",
            "field_path": "product_tmpl_id.product_variant_ids.default_code",
            "font_mm": 3, "max_lines": 1,
        }]}
        with self.assertRaises(ValidationError):
            self._template(design)

    def test_collection_aggregates_are_deterministic(self):
        base = {
            "id": "variants", "type": "text", "x_mm": 1, "y_mm": 1,
            "w_mm": 40, "h_mm": 5, "source": "field",
            "field_path": "product_tmpl_id.product_variant_ids.default_code",
            "font_mm": 3, "max_lines": 1,
        }
        design = {"version": 2, "elements": [{**base, "aggregate": "join", "separator": " | "}]}
        template = self._template(design)
        value = template.resolve_elements(self.product)[0]["value_resolved"]
        self.assertIn("ICK-001", value)
        design_count = {"version": 2, "elements": [{**base, "aggregate": "count"}]}
        template_count = self._template(design_count, name="Count")
        self.assertGreaterEqual(int(template_count.resolve_elements(self.product)[0]["value_resolved"]), 1)


    def test_image_field_catalog_and_zpl_bitmap(self):
        image_b64 = (
            "iVBORw0KGgoAAAANSUhEUgAAAAgAAAAICAIAAABLbSncAAAAMklEQVR4nG3LQQoAQAgC"
            "QPX/f3YPQVhtF4UxArCNc7JN8gP1cU0V19RtmXKVNiBtQ9sDmwcYDTEMfWwAAAAASUVORK5CYII="
        )
        self.product.image_1920 = image_b64.encode("ascii")
        catalog = self.env["ickab.label.template"].get_field_catalog(self.model.id, "")
        image_field = next(field for field in catalog["fields"] if field["name"] == "image_1920")
        self.assertTrue(image_field["is_image"])

        design = {"version": 2, "elements": [{
            "id": "photo", "type": "image", "x_mm": 2, "y_mm": 2,
            "w_mm": 20, "h_mm": 15, "source": "field",
            "field_path": "image_1920", "fit": "contain",
            "threshold": 128, "dither": "none", "invert": False,
        }]}
        template = self._template(design, name="Imagen producto")
        element = template.resolve_elements(self.product)[0]
        self.assertTrue(element["preview_src"].startswith("data:image/png;base64,"))
        self.assertTrue(element["image_bitmap_b64"])
        self.assertGreater(element["image_bytes_per_row"], 0)
        zpl = template.generate_zpl(self.product)
        self.assertIn("^GFA,", zpl)

    def test_company_logo_image_is_valid_without_business_record(self):
        design = {"version": 2, "elements": [{
            "id": "logo", "type": "image", "x_mm": 1, "y_mm": 1,
            "w_mm": 20, "h_mm": 10, "source": "company_logo",
            "fit": "contain", "threshold": 128, "dither": "none",
        }]}
        template = self._template(design, name="Logo empresa")
        parsed = template._parse_design(strict=True, validate_fields=True)
        self.assertEqual(parsed["elements"][0]["type"], "image")

    def test_image_binary_size_placeholder_is_not_treated_as_base64(self):
        template = self._template(name="Normalización imagen")
        self.assertEqual(template._normalize_image_b64("24.6 KB"), "")
        self.assertEqual(template._normalize_image_b64(b"24.6 KB"), "")

    def test_image_render_forces_real_binary_when_bin_size_context_is_present(self):
        image_b64 = (
            "iVBORw0KGgoAAAANSUhEUgAAAAgAAAAICAIAAABLbSncAAAAMklEQVR4nG3LQQoAQAgC"
            "QPX/f3YPQVhtF4UxArCNc7JN8gP1cU0V19RtmXKVNiBtQ9sDmwcYDTEMfWwAAAAASUVORK5CYII="
        )
        self.product.image_1920 = image_b64.encode("ascii")
        design = {"version": 2, "elements": [{
            "id": "photo-bin-size", "type": "image", "x_mm": 2, "y_mm": 2,
            "w_mm": 20, "h_mm": 15, "source": "field",
            "field_path": "image_1920", "fit": "contain",
            "threshold": 128, "dither": "none", "invert": False,
        }]}
        template = self._template(design, name="Imagen con bin_size")
        product = self.product.with_context(bin_size=True)
        element = template.with_context(bin_size=True).resolve_elements(product)[0]
        self.assertTrue(element["preview_src"].startswith("data:image/png;base64,"))
        self.assertTrue(element["image_bitmap_b64"])

    def test_image_processor_recovers_double_base64(self):
        image_b64 = (
            "iVBORw0KGgoAAAANSUhEUgAAAAgAAAAICAIAAABLbSncAAAAMklEQVR4nG3LQQoAQAgC"
            "QPX/f3YPQVhtF4UxArCNc7JN8gP1cU0V19RtmXKVNiBtQ9sDmwcYDTEMfWwAAAAASUVORK5CYII="
        )
        double_b64 = base64.b64encode(image_b64.encode("ascii")).decode("ascii")
        payload = self.env["ickab.label.image.processor"].prepare_bitmap(
            double_b64,
            80,
            40,
            options={"fit": "contain", "threshold": 128, "dither": "none"},
            image_label="image_1920",
        )
        self.assertEqual(payload["image_format"], "PNG")
        self.assertEqual(payload["image_bytes_per_row"], 10)
        self.assertEqual(len(base64.b64decode(payload["image_bitmap_b64"])), 400)

    def test_webp_processor_is_isolated_from_odoo_pillow_registry(self):
        # Tiny static WebP fixture.  Odoo 18 intentionally locks Pillow after
        # preinit(), so WebP is normally absent from Image.OPEN inside workers.
        webp_b64 = (
            "UklGRkQAAABXRUJQVlA4IDgAAADQAgCdASoRAAsAPm0skkWkIqGYBABABsSgB2AA"
            "EDYAAP7rZF//+sr/9ZX/6yv98j/90GWcM5gAAA=="
        )
        before_initialized = Image._initialized
        before_webp_open = "WEBP" in Image.OPEN
        before_webp_id = "WEBP" in Image.ID

        payload = self.env["ickab.label.image.processor"].prepare_bitmap(
            webp_b64,
            80,
            40,
            options={"fit": "contain", "threshold": 128, "dither": "none"},
            image_label="image_1920",
        )

        self.assertEqual(payload["image_format"], "WEBP")
        self.assertTrue(payload["image_preview_src"].startswith("data:image/png;base64,"))
        self.assertTrue(payload["image_bitmap_b64"])
        self.assertEqual(Image._initialized, before_initialized)
        self.assertEqual("WEBP" in Image.OPEN, before_webp_open)
        self.assertEqual("WEBP" in Image.ID, before_webp_id)

    def test_invalid_base64_image_reports_source_without_translation_crash(self):
        invalid = base64.b64encode(b"THIS IS VALID BASE64 BUT NOT AN IMAGE").decode("ascii")
        with self.assertRaises(UserError) as caught:
            self.env["ickab.label.image.processor"].prepare_bitmap(
                invalid,
                80,
                40,
                options={"fit": "contain"},
                image_label="image_1920",
            )
        message = str(caught.exception)
        self.assertIn("image_1920", message)
        self.assertNotIn("get_text_alias", message)

    def test_company_logo_is_actually_rasterized(self):
        design = {"version": 2, "elements": [{
            "id": "logo-render", "type": "image", "x_mm": 1, "y_mm": 1,
            "w_mm": 20, "h_mm": 10, "source": "company_logo",
            "fit": "contain", "threshold": 128, "dither": "none",
        }]}
        template = self._template(design, name="Logo empresa raster")
        element = template.resolve_elements()[0]
        self.assertTrue(element["image_bitmap_b64"])
        self.assertTrue(element["preview_src"].startswith("data:image/png;base64,"))
        self.assertTrue(element["image_source_label"].startswith("res."))

    def test_multiline_text_is_preserved_in_zpl(self):
        design = {"version": 2, "elements": [{
            "id": "multi", "type": "text", "x_mm": 1, "y_mm": 1,
            "w_mm": 30, "h_mm": 12, "source": "static",
            "value": "LINEA 1\nLINEA_2", "font_mm": 3, "max_lines": 2,
        }]}
        zpl = self._template(design).generate_zpl()
        self.assertIn("^FH_", zpl)
        self.assertIn(r"LINEA 1\&LINEA_5F2", zpl)

    def test_zpl_parser_is_conservative_for_lossy_layout_commands(self):
        parsed = self.env["ickab.label.zpl.parser"].parse(
            "^XA^PW400^LL240^LT10^FT20,50^A0N,30,30^FDHELLO^FS^XZ", dpi=203
        )
        self.assertFalse(parsed["fully_editable"])
        self.assertIn("^LT", parsed["unsupported"])
        self.assertIn("^FT", parsed["unsupported"])
        self.assertTrue(parsed["design"]["elements"])

    def test_zpl_parser_truncates_preview_but_reports_raw_requirement(self):
        body = "".join(f"^FO1,{i % 200}^GB2,2,1^FS" for i in range(510))
        parsed = self.env["ickab.label.zpl.parser"].parse(f"^XA^PW400^LL400{body}^XZ", dpi=203)
        self.assertTrue(parsed["preview_truncated"])
        self.assertFalse(parsed["fully_editable"])
        self.assertEqual(len(parsed["design"]["elements"]), 500)
        self.assertEqual(parsed["visual_count"], 510)

    def test_force_editable_rejects_lossy_zpl(self):
        wizard = self.env["ickab.label.zpl.import.wizard"].create({
            "template_name": "Lossy",
            "source_dpi": "203",
            "import_mode": "editable",
            "source_zpl": "^XA^PW400^LL240^FT20,50^A0N,30,30^FDHELLO^FS^XZ",
        })
        with self.assertRaises(UserError):
            wizard.action_import()


    def test_direct_print_integration_is_embedded_without_external_field_dependency(self):
        template = self._template()
        self.assertTrue(hasattr(template, "action_direct_print"))
        self.assertTrue(hasattr(template, "_direct_print_prepare_data"))
        self.assertNotIn("ickab_paper_id", template._fields)
        self.assertIn("direct_print_available", template._fields)

    def test_direct_print_runtime_check_does_not_require_module_install(self):
        template = self._template()
        available = template._direct_print_runtime_available()
        self.assertIsInstance(available, bool)

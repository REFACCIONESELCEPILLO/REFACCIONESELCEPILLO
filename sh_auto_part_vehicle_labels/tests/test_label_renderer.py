# -*- coding: utf-8 -*-
from odoo.tests.common import TransactionCase


class TestAutoPartLabelRenderer(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.renderer = cls.env["sh.auto.part.vehicle.label.renderer"]
        cls.product = cls.env["product.product"].create({
            "name": "Producto prueba Auto Part",
            "default_code": "RDNN0900",
            "barcode": "7501234567890",
        })
        cls.data = {
            "code": "RDNN0900",
            "name": "BALERO DELANTERO NS MARCH VERSA C/ABS FT RAM 700",
            "barcode": "RDNN0900",
            "oem": [
                {"brand": "NIKKO", "code": "40210-AX000-TW"},
                {"brand": "NIKKO", "code": "40210-1HA1A-TW"},
                {"brand": "SYD-SUSPENSIONES", "code": "2216009-SYD"},
                {"brand": "Por definir", "code": "7701207677-TMK"},
            ],
        }

    def test_mm_to_dots(self):
        self.assertEqual(self.renderer._mm_to_dots(50, 203), 400)
        self.assertEqual(self.renderer._mm_to_dots(30, 203), 240)

    def test_50x30_plan_contains_header_name_oem(self):
        plan = self.renderer.build_plan(self.data, self.renderer.FORMAT_50_30)
        texts = [e for e in plan["elements"] if e["type"] == "text"]
        self.assertTrue(any(e.get("role") == "sku_label" and e["text"] == "SKU:" for e in texts))
        self.assertTrue(any(e.get("role") == "code" and e["text"] == "RDNN0900" for e in texts))
        self.assertTrue(any("BALERO DELANTERO" in e["text"] for e in texts))
        self.assertTrue(any("NIKKO: 40210-AX000-TW" == e["text"] for e in texts))

    def test_plan_has_no_renderer_specific_coordinates(self):
        plan = self.renderer.build_plan(self.data, self.renderer.FORMAT_50_30)
        code = next(e for e in plan["elements"] if e.get("role") == "code")
        name = next(e for e in plan["elements"] if e.get("role") == "name")
        oem = next(e for e in plan["elements"] if e.get("role") == "oem")
        self.assertLess(code["y"], name["y"])
        self.assertLess(name["y"], oem["y"])

    def test_50x30_uses_standardized_header_and_logo(self):
        data = dict(self.data, logo=b"aGVsbG8=")
        plan = self.renderer.build_plan(data, self.renderer.FORMAT_50_30)
        logo = next(e for e in plan["elements"] if e.get("role") == "logo")
        self.assertEqual((logo["x"], logo["y"], logo["w"], logo["h"]), (1.0, 1.5, 14.5, 5.5))
        code = next(e for e in plan["elements"] if e.get("role") == "code")
        names = [e for e in plan["elements"] if e.get("role") == "name"]
        oem = next(e for e in plan["elements"] if e.get("role") == "oem")
        self.assertEqual((code["x"], code["y"]), (22.0, 3.0))
        self.assertGreater(code["font_mm"], names[0]["font_mm"])
        self.assertGreater(names[0]["font_mm"], oem["font_mm"])
        self.assertEqual(len(names), 2)

    def test_50x30_fixed_tspl_maps_to_native_fonts_2_2_1_for_four_oems(self):
        profile = self.env["ickab.print.compatibility.profile"].create({
            "name": "TSPL fixed physical test",
            "language": "tspl",
            "dpi": "203",
            "printer_type": "label",
            "tspl_scalable_font0": False,
        })
        plan = self.renderer.build_plan(self.data, self.renderer.FORMAT_50_30)
        code = next(e for e in plan["elements"] if e.get("role") == "code")
        name = next(e for e in plan["elements"] if e.get("role") == "name")
        oem = next(e for e in plan["elements"] if e.get("role") == "oem")
        self.assertIn('"2",0,1,1', self.renderer._tspl_text_command(code, 203, profile).decode("cp850"))
        self.assertIn('"2",0,1,1', self.renderer._tspl_text_command(name, 203, profile).decode("cp850"))
        self.assertIn('"1",0,1,1', self.renderer._tspl_text_command(oem, 203, profile).decode("cp850"))


    def test_50x30_name_wraps_complete_with_physical_font_pitch(self):
        plan = self.renderer.build_plan(self.data, self.renderer.FORMAT_50_30)
        names = [e["text"] for e in plan["elements"] if e.get("role") == "name"]
        self.assertEqual(names, [
            "BALERO DELANTERO NS MARCH",
            "VERSA C/ABS FT RAM 700",
        ])
        self.assertNotIn("...", " ".join(names))

    def test_50x30_dense_oem_block_falls_back_to_compact_font(self):
        data = dict(self.data)
        data["oem"] = [
            {"brand": "MARCA", "code": "SKU-%s" % i}
            for i in range(1, 8)
        ]
        profile = self.env["ickab.print.compatibility.profile"].create({
            "name": "TSPL dense OEM physical test",
            "language": "tspl",
            "dpi": "203",
            "printer_type": "label",
            "tspl_scalable_font0": False,
        })
        plan = self.renderer.build_plan(data, self.renderer.FORMAT_50_30)
        oems = [e for e in plan["elements"] if e.get("role") == "oem"]
        self.assertEqual(len(oems), 7)
        self.assertTrue(all(e.get("density") == "compact" for e in oems))
        self.assertIn('"1",0,1,1', self.renderer._tspl_text_command(oems[0], 203, profile).decode("cp850"))

    def test_50x30_has_no_barcode(self):
        plan = self.renderer.build_plan(self.data, self.renderer.FORMAT_50_30)
        self.assertFalse(any(e["type"] == "barcode" for e in plan["elements"]))

    def test_100x50_has_requested_geometry(self):
        data = dict(self.data, logo=b"aGVsbG8=")
        plan = self.renderer.build_plan(data, self.renderer.FORMAT_100_50)
        self.assertEqual((plan["width_mm"], plan["height_mm"]), (100.0, 50.0))
        logo = next(e for e in plan["elements"] if e.get("role") == "logo")
        self.assertEqual((logo["x"], logo["y"], logo["w"], logo["h"]), (2.0, 3.0, 29.0, 11.0))
        sku = next(e for e in plan["elements"] if e.get("role") == "sku_label")
        code = next(e for e in plan["elements"] if e.get("role") == "code")
        self.assertEqual((sku["x"], sku["y"], sku["font_mm"]), (32.0, 7.0, 3.0))
        self.assertEqual((code["x"], code["y"], code["font_mm"]), (43.0, 6.0, 5.0))
        barcode = next(e for e in plan["elements"] if e["type"] == "barcode")
        self.assertEqual((barcode["x"], barcode["y"], barcode["w"], barcode["h"]), (24.5, 35.0, 51.0, 10.0))
        barcode_text = next(e for e in plan["elements"] if e.get("role") == "barcode_text")
        self.assertEqual((barcode_text["x"], barcode_text["y"], barcode_text["font_mm"], barcode_text["align"]), (24.5, 46.0, 3.0, "C"))

    def test_tspl2_scalable_font_preserves_text_hierarchy(self):
        profile = self.env["ickab.print.compatibility.profile"].create({
            "name": "TSPL2 Test",
            "language": "tspl",
            "dpi": "203",
            "printer_type": "label",
            "tspl_scalable_font0": True,
        })
        plan = self.renderer.build_plan(self.data, self.renderer.FORMAT_50_30)
        code = next(e for e in plan["elements"] if e.get("role") == "code")
        name = next(e for e in plan["elements"] if e.get("role") == "name")
        oem = next(e for e in plan["elements"] if e.get("role") == "oem")
        code_cmd = self.renderer._tspl_text_command(code, 203, profile).decode("cp850")
        name_cmd = self.renderer._tspl_text_command(name, 203, profile).decode("cp850")
        oem_cmd = self.renderer._tspl_text_command(oem, 203, profile).decode("cp850")
        self.assertIn('"0",0,7,7', code_cmd)
        self.assertIn('"0",0,6,6', name_cmd)
        self.assertIn('"0",0,4,4', oem_cmd)

    def test_canonical_coordinates_are_used_by_tspl(self):
        profile = self.env["ickab.print.compatibility.profile"].create({
            "name": "TSPL Fixed Test",
            "language": "tspl",
            "dpi": "203",
            "printer_type": "label",
        })
        plan = self.renderer.build_plan(self.data, self.renderer.FORMAT_50_30)
        code = next(e for e in plan["elements"] if e.get("role") == "code")
        cmd = self.renderer._tspl_text_command(code, 203, profile).decode("cp850")
        expected_xy = "%s,%s" % (
            self.renderer._mm_to_dots(code["x"], 203),
            self.renderer._mm_to_dots(code["y"], 203),
        )
        self.assertIn("TEXT %s," % expected_xy, cmd)

    def test_direct_print_source_does_not_choose_language(self):
        source = self.renderer.build_print_source([(self.product, 2)], "auto_part_zpl_50_30")
        self.assertEqual(source["kind"], "label")
        document = source["documents"][0]
        self.assertEqual(document["mode"], "fixed")
        self.assertEqual(document["copies"], 2)
        self.assertNotIn("language", document)


# -*- coding: utf-8 -*-
from odoo.exceptions import UserError
from odoo.tests.common import TransactionCase


class TestPrinterCompatibility(TransactionCase):

    def setUp(self):
        super().setUp()
        self.host = self.env["ickab.print.host"].create({"name": "Test Host"})

    def _printer(self, **extra):
        vals = {
            "name": "4BARCODE 4B-2054L",
            "host_id": self.host.id,
            "company_id": self.env.company.id,
            "printer_type": "label",
            "transport": "windows_raw",
            "language": "tspl",
            "dpi": "203",
        }
        vals.update(extra)
        return self.env["ickab.print.printer"].create(vals)

    def test_profile_suggestion_4barcode(self):
        printer = self._printer()
        profile = self.env.ref("ickab_direct_print.compat_4barcode_4b2054l")
        self.assertEqual(printer.suggested_compatibility_profile_id, profile)

    def test_apply_profile_does_not_change_transport(self):
        printer = self._printer(transport="windows_raw", language="raw", dpi="na")
        printer.compatibility_profile_id = self.env.ref("ickab_direct_print.compat_4barcode_4b2054l")
        printer.action_apply_compatibility_profile()
        self.assertEqual(printer.transport, "windows_raw")
        self.assertEqual(printer.language, "tspl")
        self.assertEqual(printer.dpi, "203")

    def test_tspl_payload_is_accepted(self):
        printer = self._printer()
        job = self.env["ickab.print.job"].enqueue(
            printer=printer,
            payload_type="tspl",
            payload='SIZE 50 mm,30 mm\r\nCLS\r\nPRINT 1,1\r\n',
        )
        self.assertEqual(job.payload_type, "tspl")
        self.assertTrue(job._raw_payload().startswith(b"SIZE 50 mm"))

    def test_zpl_rejected_on_tspl_printer(self):
        printer = self._printer()
        with self.assertRaises(UserError):
            self.env["ickab.print.job"].enqueue(
                printer=printer,
                payload_type="zpl",
                payload="^XA^XZ",
            )


    def test_tspl_binary_payload_survives_reprint(self):
        printer = self._printer()
        payload = b"SIZE 50 mm,30 mm\r\nCLS\r\nBITMAP 0,0,1,1,0," + bytes([0xFF]) + b"\r\nPRINT 1,1\r\n"
        job = self.env["ickab.print.job"].enqueue(
            printer=printer,
            payload_type="tspl",
            payload=payload,
        )
        self.assertEqual(job._raw_payload(), payload)
        job.action_reprint()
        copy = self.env["ickab.print.job"].search([
            ("printer_id", "=", printer.id),
            ("id", "!=", job.id),
        ], order="id desc", limit=1)
        self.assertTrue(copy)
        self.assertEqual(copy._raw_payload(), payload)


    def test_zebra_epl_queue_can_negotiate_zpl_from_profile(self):
        self.host.write({"platform_type": "windows"})
        zebra = self._printer(
            name="ZDesigner GK420d (EPL)",
            system_name="ZDesigner GK420d (EPL)",
            transport="windows_spooler",
            language="epl",
            compatibility_profile_id=self.env.ref("ickab_direct_print.compat_zebra_gk420d").id,
        )
        self.assertIn("zpl", zebra._ickab_supported_languages())
        self.assertEqual(self.env["ickab.print.engine"]._select_label_renderer(zebra), "zpl")

    def test_unknown_label_language_uses_pdf_driver_fallback(self):
        self.host.write({"platform_type": "windows"})
        printer = self._printer(
            name="Etiqueta con driver",
            system_name="Etiqueta con driver",
            transport="windows_spooler",
            language="epl",
        )
        self.assertEqual(self.env["ickab.print.engine"]._select_label_renderer(printer), "pdf")
        self.assertIn("pdf", printer.accepted_payload_types())

    def test_4barcode_profile_owns_tspl_physical_capabilities(self):
        profile = self.env.ref("ickab_direct_print.compat_4barcode_4b2054l")
        self.assertEqual(profile.label_direction, "1")
        self.assertFalse(profile.tspl_bitmap_one_is_black)
        self.assertTrue(profile.supports_inline_bitmap)
        self.assertFalse(profile.tspl_scalable_font0)

    def test_tspl_test_and_generators_share_preamble_contract(self):
        printer = self._printer()
        printer.compatibility_profile_id = self.env.ref("ickab_direct_print.compat_4barcode_4b2054l")
        paper = self.env.ref("ickab_direct_print.paper_label_50x30")
        preamble = printer._ickab_tspl_preamble(50, 30, paper=paper)
        self.assertIn("SIZE 50 mm,30 mm\r\n", preamble)
        self.assertIn("GAP 2 mm,0 mm\r\n", preamble)
        self.assertIn("DIRECTION 1\r\n", preamble)
        self.assertIn("REFERENCE 0,0\r\n", preamble)
        self.assertTrue(printer._test_tspl(paper).startswith(preamble))

    def test_zpl_test_uses_canonical_preamble(self):
        zebra = self.env["ickab.print.printer"].create({
            "name": "Zebra GK420d",
            "host_id": self.host.id,
            "company_id": self.env.company.id,
            "printer_type": "label",
            "transport": "windows_raw",
            "language": "zpl",
            "dpi": "203",
            "compatibility_profile_id": self.env.ref("ickab_direct_print.compat_zebra_gk420d").id,
        })
        paper = self.env.ref("ickab_direct_print.paper_label_50x30")
        preamble = zebra._ickab_zpl_preamble(50, 30, dpi=203)
        self.assertIn("^PW400", preamble)
        self.assertIn("^LL240", preamble)
        self.assertTrue(zebra._test_zpl(paper).startswith(preamble))

from odoo.tests.common import TransactionCase


class TestDirectPrint(TransactionCase):
    def test_default_papers_exist(self):
        self.assertTrue(self.env.ref("ickab_direct_print.paper_label_50x30"))
        self.assertTrue(self.env.ref("ickab_direct_print.paper_letter"))

    def test_job_payload(self):
        host = self.env["ickab.print.host"].create({"name": "TEST"})
        printer = self.env["ickab.print.printer"].create({
            "name": "Zebra", "host_id": host.id, "printer_type": "label",
            "transport": "tcp_raw", "language": "zpl", "dpi": "203",
            "network_host": "127.0.0.1", "network_port": 9100,
        })
        job = self.env["ickab.print.job"].enqueue(printer=printer, payload_type="zpl", payload="^XA^XZ")
        self.assertEqual(job._raw_payload(), b"^XA^XZ")

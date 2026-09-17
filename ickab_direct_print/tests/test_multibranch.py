from odoo.tests.common import TransactionCase


class TestDirectPrintMultiBranch(TransactionCase):
    def test_branch_host_user_assignment_and_job_context(self):
        company = self.env.company
        user = self.env.user

        branch = self.env["ickab.print.branch"].create({
            "name": "Sucursal Prueba",
            "code": "TEST-BRANCH",
            "company_id": company.id,
        })
        self.env["ickab.print.user.branch"].create({
            "user_id": user.id,
            "branch_id": branch.id,
            "is_default": True,
        })

        host = self.env["ickab.print.host"].create({
            "name": "PC SUCURSAL PRUEBA",
            "company_id": company.id,
            "branch_id": branch.id,
        })
        self.assertEqual(host.branch_id, branch)

        printer = self.env["ickab.print.printer"].create({
            "name": "Zebra Prueba",
            "company_id": company.id,
            "host_id": host.id,
            "printer_type": "label",
            "transport": "windows_spooler",
            "language": "zpl",
            "dpi": "203",
        })
        self.assertEqual(printer.branch_id, branch)
        self.assertEqual(user._ickab_resolve_print_branch(company), branch)

        assignment = self.env["ickab.print.assignment"].create({
            "company_id": company.id,
            "branch_id": branch.id,
            "user_id": user.id,
            "document_kind": "label",
            "printer_id": printer.id,
            "is_default": True,
        })
        resolved = self.env["ickab.print.assignment"].resolve_assignment(
            "label", user=user, company=company, branch=branch
        )
        self.assertEqual(resolved, assignment)

        job = self.env["ickab.print.job"].enqueue(
            printer=printer,
            payload_type="zpl",
            payload="^XA^XZ",
            branch=branch,
        )
        self.assertEqual(job.branch_id, branch)
        context = self.env["ickab.print.job.context"].search([("job_id", "=", job.id)])
        self.assertEqual(context.branch_id, branch)

from odoo.tests import tagged
from odoo.tests.common import TransactionCase
from odoo.exceptions import AccessError


@tagged("post_install", "-at_install")
class TestSaleOrderLock(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.partner = cls.env["res.partner"].create({"name": "Cliente bloqueo"})

    def test_saved_quotation_is_locked(self):
        order = self.env["sale.order"].create({"partner_id": self.partner.id})
        self.assertTrue(order.blocked_order)

    def test_unlock_is_temporary_until_next_save(self):
        order = self.env["sale.order"].create({"partner_id": self.partner.id})
        order.action_unlock_order()
        self.assertFalse(order.blocked_order)

        order.write({"client_order_ref": "CAMBIO AUTORIZADO"})
        self.assertTrue(order.blocked_order)
        self.assertEqual(order.client_order_ref, "CAMBIO AUTORIZADO")

    def test_salesperson_cannot_unlock(self):
        salesperson = self.env["res.users"].create({
            "name": "Vendedor sin desbloqueo",
            "login": "test_sale_restring_salesperson",
            "groups_id": [(6, 0, [
                self.env.ref("base.group_user").id,
                self.env.ref("sales_team.group_sale_salesman").id,
            ])],
        })
        order = self.env["sale.order"].create({"partner_id": self.partner.id})
        with self.assertRaises(AccessError):
            order.with_user(salesperson).action_unlock_order()

from odoo import _, api, fields, models
from odoo.exceptions import AccessError

class SaleOrder(models.Model):
	_inherit = "sale.order"

	blocked_order = fields.Boolean(
		string="Orden bloqueada",
		default=False,
		copy=False,
	)

	def action_unlock_order(self):
		"""Open the order for one editing cycle.

		The next regular save locks it again.  Access to this action is
		restricted in the form view to the dedicated unlock group.
		"""
		if not self.env.user.has_group("sale_restring.group_sale_locked"):
			raise AccessError(_("No tiene permisos para desbloquear cotizaciones."))
		self.with_context(unlock_sale_order=True).write({"blocked_order": False})
		return True

	@api.model_create_multi
	def create(self, vals_list):
		"""Lock back-office quotations as soon as they receive a folio."""
		for values in vals_list:
			# Website orders keep their native checkout workflow.
			if not values.get("website_id"):
				values["blocked_order"] = True
		return super().create(vals_list)

	def action_confirm(self):
		"""Confirmed sales orders always remain protected."""
		result = super().action_confirm()
		super(SaleOrder, self).write({"blocked_order": True})
		return result

	def action_draft(self):
		"""A quotation returned to draft is still a saved, locked record."""
		result = super().action_draft()
		super(SaleOrder, self).write({"blocked_order": True})
		return result

	def write(self, values):
		"""Relock a quotation after every normal save.

		Using ``super`` for the final technical write avoids recursion while
		keeping the unlock action as the only supported way to clear the flag.
		"""
		result = super().write(values)
		if self.env.context.get("unlock_sale_order"):
			return result
		has_website = "website_id" in self._fields
		to_lock = self.filtered(
			lambda order: (
				(not has_website or not order.website_id)
				and not order.blocked_order
			)
		)
		if to_lock:
			super(SaleOrder, to_lock).write({"blocked_order": True})
		return result

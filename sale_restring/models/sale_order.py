from odoo import fields, models

class SaleOrder(models.Model):
	_inherit = "sale.order"

	blocked_order = fields.Boolean(
		string="Orden bloqueada",
		default=False,
		copy=False,
	)

	def action_unlock_order(self):
		"""Allow an authorized user to edit a confirmed sales order."""
		self.write({"blocked_order": False})

	def action_confirm(self):
		"""Lock only after the quotation becomes a sales order."""
		result = super().action_confirm()
		self.write({"blocked_order": True})
		return result

	def action_draft(self):
		"""A quotation returned to draft must be editable again."""
		result = super().action_draft()
		self.write({"blocked_order": False})
		return result

	def write(self, values):
		# Autosaves and line changes preserve the current decision. Confirmation
		# and return-to-draft are handled by their explicit business actions.
		return super().write(values)

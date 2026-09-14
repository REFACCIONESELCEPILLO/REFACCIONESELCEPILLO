from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    ickab_direct_print_enabled = fields.Boolean(
        related="company_id.ickab_direct_print_enabled",
        readonly=False,
    )
    ickab_default_label_printer_id = fields.Many2one(
        related="company_id.ickab_default_label_printer_id",
        readonly=False,
    )
    ickab_default_label_paper_id = fields.Many2one(
        related="company_id.ickab_default_label_paper_id",
        readonly=False,
    )
    ickab_default_ticket_printer_id = fields.Many2one(
        related="company_id.ickab_default_ticket_printer_id",
        readonly=False,
    )
    ickab_default_ticket_paper_id = fields.Many2one(
        related="company_id.ickab_default_ticket_paper_id",
        readonly=False,
    )
    ickab_default_document_printer_id = fields.Many2one(
        related="company_id.ickab_default_document_printer_id",
        readonly=False,
    )
    ickab_default_document_paper_id = fields.Many2one(
        related="company_id.ickab_default_document_paper_id",
        readonly=False,
    )

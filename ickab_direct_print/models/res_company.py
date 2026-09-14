from odoo import fields, models


class ResCompany(models.Model):
    _inherit = "res.company"

    ickab_direct_print_enabled = fields.Boolean(string="Habilitar ICKAB Direct Print")

    ickab_default_label_printer_id = fields.Many2one(
        "ickab.print.printer",
        string="Impresora de etiquetas predeterminada",
        domain="[('company_id', '=', id), ('printer_type', '=', 'label'), ('active', '=', True)]",
    )
    ickab_default_label_paper_id = fields.Many2one(
        "ickab.print.paper",
        string="Papel de etiquetas predeterminado",
        domain="['|', ('company_id', '=', False), ('company_id', '=', id), ('category', '=', 'label')]",
    )
    ickab_default_ticket_printer_id = fields.Many2one(
        "ickab.print.printer",
        string="Impresora de tickets predeterminada",
        domain="[('company_id', '=', id), ('printer_type', '=', 'ticket'), ('active', '=', True)]",
    )
    ickab_default_ticket_paper_id = fields.Many2one(
        "ickab.print.paper",
        string="Papel de tickets predeterminado",
        domain="['|', ('company_id', '=', False), ('company_id', '=', id), ('category', '=', 'ticket')]",
    )
    ickab_default_document_printer_id = fields.Many2one(
        "ickab.print.printer",
        string="Impresora de documentos predeterminada",
        domain="[('company_id', '=', id), ('printer_type', '=', 'document'), ('active', '=', True)]",
    )
    ickab_default_document_paper_id = fields.Many2one(
        "ickab.print.paper",
        string="Papel de documentos predeterminado",
        domain="['|', ('company_id', '=', False), ('company_id', '=', id), ('category', '=', 'document')]",
    )

# -*- coding: utf-8 -*-
# Part of Softhealer Technologies.
from odoo import fields, models
from odoo.fields import Date


class SaleOrder(models.Model):
    _inherit = "sale.order"
    _description = "sale order"
    # _order = "sequence"

   
    

    # def viewQuotation(self,domain):
    #     return {
    #         'name': 'viewQuotation',
    #         'type': 'ir.actions.act_window',
    #         'view_mode': 'list, form',
    #         'views': [(self.env.ref('sale.view_quotation_tree_with_onboarding').id,'list'),
    #                   (self.env.ref('sale.view_order_form').id,'form')],
    #         'domain': domain,
    #         'res_model': 'sale.order',
    #         'context': dict(create=False),
    #         'target': 'current',


    #     }
    

    def viewQuotation(self, domain=None):
        return {
            'name': 'viewQuotation',
            'type': 'ir.actions.act_window',
            'view_mode': 'list, form',
            'views': [(self.env.ref('sale.view_quotation_tree_with_onboarding').id, 'list'),
                    (self.env.ref('sale.view_order_form').id, 'form')],
            'domain': domain or [],
            'res_model': 'sale.order',
            'context': dict(create=False),
            'target': 'current',
        }

    

    
    # def viewSaleOrder(self, domain=None):
    #     domain = domain or [['state', '=', 'sale']]  

    #     return {
    #         'name': 'Sale Orders',
    #         'type': 'ir.actions.act_window',
    #         'view_mode': 'list ,form',
    #         'views': [(self.env.ref('sale.sale_order_list_upload').id, 'list'),
    #                   (self.env.ref('sale.view_order_form').id, 'form')],  
    #         'res_model': 'sale.order',
    #         'domain': domain or [],  
    #         'context': {'create': False},
    #         'target': 'current',
    #     }
    

    def viewSaleOrder(self, domain=None):
        base_domain = [['state', '=', 'sale']]

        if domain:
            domain = ['&'] + domain + base_domain   # AND condition
        else:
            domain = base_domain 
        return {
            'name': 'Sale Orders',
            'type': 'ir.actions.act_window',
            'view_mode': 'list,form',
            'views': [(self.env.ref('sale.sale_order_list_upload').id, 'list'),
                    (self.env.ref('sale.view_order_form').id, 'form')],  
            'res_model': 'sale.order',
            'domain': domain,  
            'context': {'create': False},
            'target': 'current',
        }





    



class Invoice(models.Model):


    _inherit="account.move"




    # def Invoice(self, domain=None):
    #         domain = domain or [["payment_state", "in", ["paid", "partial", "in_payment"]]]
    #         return {
    #             'name': 'Invoice',
    #             'type': 'ir.actions.act_window',
    #             'view_mode': 'list,form',
    #             'views': [(self.env.ref('account.view_out_invoice_tree').id, 'list'),
    #                       (self.env.ref('account.view_move_form').id, 'form')],  
    #             'res_model': 'account.move',
    #             'domain': domain or [],  
    #             'context': {'create': False},
    #             'target': 'current',
    #         }
    

     
    def Invoice(self, domain=None):
        base_domain = [("move_type", "=", "out_invoice")]  # Just customer invoices

        if domain:
            domain = ['&'] + domain + base_domain
        else:
            domain = base_domain

        return {
            'name': 'All Invoices',
            'type': 'ir.actions.act_window',
            'view_mode': 'list,form',
            'views': [(self.env.ref('account.view_out_invoice_tree').id, 'list'),
                    (self.env.ref('account.view_move_form').id, 'form')],
            'res_model': 'account.move',
            'domain': domain,
            'context': {'create': False},
            'target': 'current',
        }

    # def Invoice(self, domain=None):
    #     base_domain = [["payment_state", "in", ["paid", "partial", "in_payment" ]]]

    #     if domain:
    #         domain = ['&'] + domain + base_domain  # Ensuring AND condition
    #     else:
    #         domain = base_domain

    #     return {
    #         'name': 'Invoice',
    #         'type': 'ir.actions.act_window',
    #         'view_mode': 'list,form',
    #         'views': [(self.env.ref('account.view_out_invoice_tree').id, 'list'),
    #                 (self.env.ref('account.view_move_form').id, 'form')],
    #         'res_model': 'account.move',
    #         'domain': domain,  
    #         'context': {'create': False},
    #         'target': 'current',
    #     }

            
    




    

    # def Overdue(self, domain=None):  
    #     # Ensure the domain filters only unpaid INVOICES (not payments)
    #     domain = domain or [
    #         ("move_type", "=", "out_invoice"),  # Only customer invoices
    #         ("payment_state", "=", "not_paid")  # Only fully unpaid invoices
    #     ]

    #     invoices = self.env["account.move"].search(domain)
    #     print("\n\n\n..Filtered Unpaid Invoices (No Payments Included)..", invoices)

    #     return {
    #         'name': 'Unpaid Invoices',
    #         'type': 'ir.actions.act_window',
    #         'view_mode': 'list,form',
    #         'views': [(self.env.ref('account.view_out_invoice_tree').id, 'list'),
    #                    (self.env.ref('account.view_move_form').id, 'form')],  
    #         'res_model': 'account.move',
    #         'domain': domain or [],  # Apply the correct filter
    #         'context': {'create': False},
    #         'target': 'current',
    #     }
    
    
    def Overdue(self, domain=None):
        today = Date.today()
        base_domain = [
            ("move_type", "=", "out_invoice"),
            ("payment_state", "=", "not_paid"),
            ("invoice_date_due", "!=", False),
            ("invoice_date_due", "<", today),
        ]

        if domain:
            domain = ['&'] + domain + base_domain
        else:
            domain = base_domain

        return {
            'name': 'Overdue Invoices',
            'type': 'ir.actions.act_window',
            'view_mode': 'list,form',
            'views': [(self.env.ref('account.view_out_invoice_tree').id, 'list'),
                    (self.env.ref('account.view_move_form').id, 'form')],
            'res_model': 'account.move',
            'domain': domain,
            'context': {'create': False},
            'target': 'current',
    }

    # def Overdue(self, domain=None):  
    #     base_domain = [
    #         ("move_type", "=", "out_invoice"),  # Only customer invoices
    #         ("payment_state", "=", "not_paid")  # Only fully unpaid invoices
    #     ]

    #     if domain:
    #         domain = ['&'] + domain + base_domain  # Ensuring AND condition
    #     else:
    #         domain = base_domain

    #     invoices = self.env["account.move"].search(domain)
    #     print("\n\n\n..Filtered Unpaid Invoices (No Payments Included)..", invoices)

    #     return {
    #         'name': 'Unpaid Invoices',
    #         'type': 'ir.actions.act_window',
    #         'view_mode': 'list,form',
    #         'views': [(self.env.ref('account.view_out_invoice_tree').id, 'list'),
    #                 (self.env.ref('account.view_move_form').id, 'form')],  
    #         'res_model': 'account.move',
    #         'domain': domain,  # Apply the correct filter
    #         'context': {'create': False},
    #         'target': 'current',
    #     }





class SaleOrderLine(models.Model):
    _inherit = "sale.order.line"

    ickab_brand_id = fields.Many2one(
        related="product_id.brand",
        string="Marca",
        readonly=True,
    )


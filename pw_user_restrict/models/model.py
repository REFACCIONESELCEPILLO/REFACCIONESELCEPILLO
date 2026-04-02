from odoo import api, fields, models, tools, _
from odoo.exceptions import UserError, AccessError
from odoo.osv import expression

# -*- coding: utf-8 -*-
from odoo import models, fields, api


class ResUsers(models.Model):
    _inherit = 'res.users'

    def write(self, values):
        self.env.user.clear_caches()
        self.env['ir.ui.view'].clear_caches()
        return super(ResUsers, self).write(values)


class ir_ui_view(models.Model):
    _inherit = 'ir.ui.view'

    def _postprocess_tag_field(self, node, name_manager, node_info):
        super()._postprocess_tag_field(node, name_manager, node_info)
        if node.tag == 'field':
            if node.get('name') == 'partner_id' and self.env.user.has_group('pw_user_restrict.group_no_create_partner'):
                options_dict = {}
                options_dict.update({"no_create": True})
                node.attrib['options'] = str(options_dict)
            if node.get('name') in ('product_id', 'product_template_id') and self.env.user.has_group('pw_user_restrict.group_no_create_product'):
                options_dict = {}
                options_dict.update({"no_create": True})
                node.attrib['options'] = str(options_dict)


class BaseModel(models.AbstractModel):
    _inherit = 'base'

    @api.model
    def _get_view(self, view_id=None, view_type='form', **options):
        arch, view = super()._get_view(view_id, view_type, **options)
        if self._name in ('product.template', 'product.product'):
            if self.env.user.has_group('pw_user_restrict.group_no_create_product'):
                arch.attrib.update({'create': 'false'})
            else:
                arch.attrib.update({'create': 'true'})

        if self._name == 'res.partner':
            if self.env.user.has_group('pw_user_restrict.group_no_create_partner'):
                arch.attrib.update({'create': 'false'})
            else:
                arch.attrib.update({'create': 'true'})
        return arch, view

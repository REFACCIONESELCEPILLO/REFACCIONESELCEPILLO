# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError

from .barcode_utils import (
    CONFIG_BARCODE_SELECTION_MAP,
    calculate_ean13_checksum,
    calculate_ean8_checksum,
    calculate_upca_checksum,
    payload_length,
)


class BarcodeGeneratorConfigRl(models.Model):
    _name = 'barcode.generator.config.rl'
    _description = 'Configuración Código de barras'
    _order = 'company_id, id desc'

    name = fields.Char(string='Nombre', required=True, default='Configuración principal')
    version = fields.Char(string='Versión', default='1.0', required=True,
                          help='Identifica la versión de reglas utilizada para generar nuevos códigos.')
    active = fields.Boolean(default=True)
    company_id = fields.Many2one(
        'res.company', string='Empresa', required=True, default=lambda self: self.env.company, index=True,
    )
    usage = fields.Selection([
        ('internal', 'Código interno de la empresa'),
        ('gs1', 'Comercial / GS1'),
    ], string='Uso', required=True, default='internal')
    default_barcode_type = fields.Selection(
        CONFIG_BARCODE_SELECTION_MAP,
        string='Tipo de barcode predeterminado',
        required=True,
        default='code128',
    )
    code_length = fields.Integer(
        string='Longitud para Code 128 / Code 39 / GS1-128',
        default=13,
        required=True,
        help='EAN-13, UPC-A y EAN-8 tienen longitud fija por estándar.',
    )
    company_prefix = fields.Char(
        string='Prefijo de empresa',
        required=True,
        default='7',
        help='Uno o varios dígitos fijos al inicio del código generado.',
    )
    category_levels = fields.Selection([
        ('0', 'Sin categoría'),
        ('1', '1 nivel: categoría padre'),
        ('2', '2 niveles: padre + hija'),
        ('3', '3 niveles: padre + hija + nieta'),
    ], string='Niveles de categoría', default='3', required=True)
    missing_level_code = fields.Char(
        string='Código para nivel inexistente',
        default='00',
        readonly=True,
        help='00 está reservado. Si el árbol no llega al nivel configurado, se usa 00.',
    )
    auto_generate_on_create = fields.Boolean(
        string='Generar automáticamente al crear producto',
        default=False,
        help='Si está activo, al crearse una variante sin barcode se genera uno al guardar.',
    )
    generate_image = fields.Boolean(
        string='Generar imagen del barcode',
        default=True,
        help='Genera y almacena la imagen utilizada por la previsualización del addon.',
    )
    sequence_digits = fields.Integer(string='Dígitos disponibles para consecutivo', compute='_compute_capacity')
    capacity_display = fields.Char(string='Capacidad teórica', compute='_compute_capacity')
    preview_category_id = fields.Many2one(
        'product.category', string='Categoría de ejemplo',
        help='Se utiliza solamente para la previsualización; no consume un consecutivo.',
    )
    preview_code = fields.Char(string='Código de ejemplo', compute='_compute_preview')
    preview_image = fields.Binary(string='Previsualización', compute='_compute_preview')
    preview_message = fields.Char(string='Estado de previsualización', compute='_compute_preview')
    manual_html = fields.Html(string='Manual de configuración', compute='_compute_manual_html', sanitize=False)

    @api.constrains('active', 'company_id')
    def _check_single_active_config(self):
        for rec in self.filtered('active'):
            other = self.search([
                ('id', '!=', rec.id),
                ('company_id', '=', rec.company_id.id),
                ('active', '=', True),
            ], limit=1)
            if other:
                raise ValidationError(_(
                    'Sólo puede existir una Configuración Código de barras activa por empresa. '
                    'Archive primero la configuración %(name)s.'
                ) % {'name': other.display_name})

    @api.constrains('company_prefix', 'code_length')
    def _check_basic_values(self):
        for rec in self:
            prefix = (rec.company_prefix or '').strip()
            if not prefix or not prefix.isdigit():
                raise ValidationError(_('El prefijo de empresa debe contener únicamente dígitos.'))
            if len(prefix) > 6:
                raise ValidationError(_('El prefijo de empresa no puede exceder 6 dígitos.'))
            if rec.code_length < 6 or rec.code_length > 32:
                raise ValidationError(_('La longitud configurable debe estar entre 6 y 32 caracteres.'))

    @api.depends('default_barcode_type', 'code_length', 'company_prefix', 'category_levels')
    def _compute_capacity(self):
        for rec in self:
            try:
                digits = rec._sequence_digit_count(rec.default_barcode_type)
            except Exception:
                digits = 0
            rec.sequence_digits = max(digits, 0)
            if digits > 18:
                rec.capacity_display = 'Estructura inválida: máximo 18 dígitos de secuencia global'
            elif digits > 0:
                capacity = (10 ** digits) - 1
                rec.capacity_display = f'{capacity:,}'.replace(',', ' ')
            else:
                rec.capacity_display = 'Sin capacidad: revise la estructura'

    def _sequence_digit_count(self, barcode_type=None):
        self.ensure_one()
        btype = barcode_type or self.default_barcode_type
        p_len = payload_length(btype, self.code_length)
        structural_len = len((self.company_prefix or '').strip()) + (int(self.category_levels or '0') * 2)
        return p_len - structural_len

    def _validate_structure(self, barcode_type=None):
        self.ensure_one()
        btype = barcode_type or self.default_barcode_type
        prefix = (self.company_prefix or '').strip()
        if not prefix or not prefix.isdigit():
            raise UserError(_('Configure un prefijo de empresa numérico.'))
        digits = self._sequence_digit_count(btype)
        if digits <= 0:
            raise UserError(_(
                'La estructura no deja espacio para el consecutivo con el tipo %(type)s. '
                'Reduzca niveles de categoría/prefijo o use un formato de mayor longitud.'
            ) % {'type': dict(CONFIG_BARCODE_SELECTION_MAP).get(btype, btype)})
        if digits > 18:
            raise UserError(_(
                'La estructura deja %(digits)s dígitos para el consecutivo, pero la secuencia global admite un máximo operativo de 18. '
                'Reduzca la longitud configurable.'
            ) % {'digits': digits})
        if digits < 4:
            raise UserError(_(
                'La estructura sólo deja %(digits)s dígitos para el consecutivo. '
                'Se requieren al menos 4 para evitar una capacidad demasiado pequeña.'
            ) % {'digits': digits})
        return True

    def _category_codes(self, category, strict=True):
        self.ensure_one()
        levels = int(self.category_levels or '0')
        if not levels:
            return []
        if not category:
            if strict:
                raise UserError(_('El producto no tiene categoría configurada.'))
            return [self.missing_level_code] * levels

        path = []
        current = category
        while current:
            path.append(current)
            current = current.parent_id
        path.reverse()

        codes = []
        for idx in range(levels):
            if idx >= len(path):
                codes.append(self.missing_level_code)
                continue
            cat = path[idx]
            code = (cat.barcode_category_code or '').strip()
            if not code:
                if strict:
                    raise UserError(_(
                        'La categoría "%(category)s" existe pero no tiene Código Barcode. '
                        'Configure su código antes de generar el barcode.'
                    ) % {'category': cat.complete_name})
                return []
            if code == self.missing_level_code:
                raise UserError(_('El código 00 está reservado para niveles inexistentes.'))
            codes.append(code)
        return codes

    def _compose_barcode(self, category, sequence_value, barcode_type=None, strict=True):
        self.ensure_one()
        btype = barcode_type or self.default_barcode_type
        self._validate_structure(btype)
        codes = self._category_codes(category, strict=strict)
        if not codes and int(self.category_levels or '0') and not strict:
            return False

        prefix = (self.company_prefix or '').strip()
        structural = prefix + ''.join(codes)
        sequence_digits = self._sequence_digit_count(btype)
        sequence_str = str(int(sequence_value)).zfill(sequence_digits)
        if len(sequence_str) > sequence_digits:
            raise UserError(_(
                'Se agotó la capacidad de %(digits)s dígitos del consecutivo para esta estructura. '
                'Cree una nueva versión de configuración con mayor capacidad.'
            ) % {'digits': sequence_digits})

        payload = structural + sequence_str
        if btype == 'ean13':
            return payload + str(calculate_ean13_checksum(payload))
        if btype == 'upca':
            return payload + str(calculate_upca_checksum(payload))
        if btype == 'ean8':
            return payload + str(calculate_ean8_checksum(payload))
        return payload

    def _next_sequence_number(self):
        self.ensure_one()
        sequence = self.env.ref('barcode_generator_rl.sequence_internal_product_barcode').sudo()
        raw = sequence.next_by_id()
        try:
            return int(raw)
        except (TypeError, ValueError):
            raise UserError(_('No fue posible obtener el siguiente consecutivo de códigos de barras.'))

    def generate_for_product(self, product, barcode_type=None, generate_image=None):
        """Generate a never-reused barcode for one variant and assign it.

        Existing barcodes are always preserved. A global sequence plus the permanent
        generation history prevents reusing a code produced by this module, even if
        a product is later deleted or the sequence is accidentally moved backwards.
        """
        self.ensure_one()
        product.ensure_one()
        if product.company_id and product.company_id != self.company_id:
            raise UserError(_(
                'El producto %(product)s pertenece a %(product_company)s y la configuración activa pertenece a %(config_company)s.'
            ) % {
                'product': product.display_name,
                'product_company': product.company_id.display_name,
                'config_company': self.company_id.display_name,
            })
        if product.barcode:
            return product.barcode

        btype = barcode_type or self.default_barcode_type
        self._validate_structure(btype)
        should_image = self.generate_image if generate_image is None else generate_image

        # Reserve attempts are deliberately bounded; under normal use the first one succeeds.
        for _attempt in range(1000):
            seq_value = self._next_sequence_number()
            candidate = self._compose_barcode(product.categ_id, seq_value, btype, strict=True)

            # Never reuse a code already present or previously generated by the module.
            already_product = self.env['product.product'].sudo().with_context(active_test=False).search_count([
                ('barcode', '=', candidate),
            ])
            already_history = self.env['barcode.generated.history.rl'].sudo().search_count([
                ('barcode', '=', candidate),
            ])
            if already_product or already_history:
                continue

            vals = {
                'barcode': candidate,
                'barcode_generation_type_rl': btype,
                'barcode_generation_config_id_rl': self.id,
                'barcode_generation_sequence_rl': str(seq_value),
                'barcode_generated_at_rl': fields.Datetime.now(),
            }
            if should_image:
                image = self.env['product.barcode.generator.rl']._generate_barcode_image(candidate, btype)
                if image:
                    vals['barcode_image'] = image
            product.with_context(skip_auto_barcode_rl=True, barcode_generator_internal_write_rl=True).write(vals)
            self.env['barcode.generated.history.rl'].sudo().create({
                'barcode': candidate,
                'product_id': product.id,
                'config_id': self.id,
                'company_id': self.company_id.id,
                'barcode_type': btype,
                'sequence_value': str(seq_value),
            })
            return candidate

        raise UserError(_(
            'No fue posible encontrar un código único después de 1,000 intentos. '
            'Revise la secuencia y la configuración.'
        ))

    @api.depends('preview_category_id', 'default_barcode_type', 'code_length', 'company_prefix', 'category_levels')
    def _compute_preview(self):
        for rec in self:
            rec.preview_code = False
            rec.preview_image = False
            rec.preview_message = False
            try:
                if int(rec.category_levels or '0') and not rec.preview_category_id:
                    rec.preview_message = _('Seleccione una Categoría de ejemplo para mostrar la previsualización.')
                    continue
                code = rec._compose_barcode(
                    rec.preview_category_id,
                    1,
                    rec.default_barcode_type,
                    strict=True,
                )
                rec.preview_code = code
                image = self.env['product.barcode.generator.rl']._generate_barcode_image(
                    code, rec.default_barcode_type
                )
                rec.preview_image = image or False
                rec.preview_message = (
                    _('Ejemplo válido. La previsualización no consume consecutivos.')
                    if image else
                    _('El código es válido, pero no fue posible renderizar la imagen. Revise la dependencia python-barcode.')
                )
            except Exception as exc:
                rec.preview_message = str(exc)

    @api.depends('usage')
    def _compute_manual_html(self):
        for rec in self:
            gs1_note = ''
            if rec.usage == 'gs1':
                gs1_note = '''
                    <div class="alert alert-warning" role="alert">
                      <b>GS1:</b> utilice únicamente un prefijo asignado oficialmente a su empresa. 
                      El generador no registra ni compra identificadores GS1.
                    </div>
                '''
            rec.manual_html = f'''
                <div class="o_form_label">
                  <h3>Manual rápido de Configuración Código de barras</h3>
                  {gs1_note}
                  <ol>
                    <li><b>Uso:</b> seleccione Interno para identificadores propios de la empresa. Para códigos comerciales use los datos asignados por GS1.</li>
                    <li><b>Tipo:</b> Code 128 es el recomendado para códigos internos flexibles. EAN-13, UPC-A y EAN-8 tienen longitud y checksum obligatorios.</li>
                    <li><b>Prefijo:</b> defina uno o varios dígitos que identifiquen a la empresa, por ejemplo <code>7</code>.</li>
                    <li><b>Categorías:</b> cada categoría utilizada debe tener un Código Barcode de 2 dígitos. <code>00</code> está reservado y significa “ese nivel no existe”. El botón “Asignar códigos a categorías” completa únicamente los faltantes, en orden de registro y por grupo de categorías hermanas.</li>
                    <li><b>Árbol incompleto:</b> si sólo existe categoría padre, los niveles hija/nieta configurados se rellenan con <code>00</code>. Si el árbol tiene más niveles de los configurados, sólo se codifican los primeros niveles desde la raíz.</li>
                    <li><b>Categoría sin código:</b> el producto se omite en procesos masivos y se reporta; nunca se inventa silenciosamente un código.</li>
                    <li><b>Consecutivo:</b> se obtiene de una secuencia global. El historial permanente impide volver a utilizar un código generado anteriormente.</li>
                    <li><b>Productos existentes:</b> el generador masivo sólo completa productos sin barcode. Nunca sustituye automáticamente un barcode existente.</li>
                    <li><b>Cambios de estructura:</b> no regenere códigos históricos. Cree/active una nueva versión y conserve la anterior archivada.</li>
                  </ol>
                  <p><b>Regla de capacidad:</b> mientras más dígitos se ocupen en prefijo y categorías, menos quedan disponibles para el consecutivo. Revise “Capacidad teórica” antes de utilizar la configuración.</p>
                </div>
            '''

    def action_validate_config(self):
        self.ensure_one()
        self._validate_structure(self.default_barcode_type)
        missing_categories = 0
        if int(self.category_levels or '0'):
            used_categories = self.env['product.product'].sudo().with_context(active_test=False).search([
                ('company_id', 'in', [False, self.company_id.id]),
            ]).mapped('categ_id')
            for category in used_categories:
                try:
                    self._category_codes(category, strict=True)
                except UserError:
                    missing_categories += 1
        msg = _(
            'Configuración válida. Consecutivo: %(digits)s dígitos. Capacidad teórica: %(capacity)s.'
        ) % {'digits': self.sequence_digits, 'capacity': self.capacity_display}
        if missing_categories:
            msg += _(' Hay %(count)s categorías utilizadas que requieren revisar su Código Barcode.') % {
                'count': missing_categories,
            }
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {'title': _('Configuración Código de barras'), 'message': msg, 'type': 'warning' if missing_categories else 'success', 'sticky': True},
        }

    def action_assign_missing_category_codes(self):
        self.ensure_one()
        categories = self.env['product.category'].sudo().search([], order='parent_id, id')
        assigned = 0
        parent_ids = set(categories.mapped('parent_id').ids)
        parent_keys = [False] + sorted(parent_ids)
        for parent_id in parent_keys:
            siblings = categories.filtered(lambda c: (c.parent_id.id or False) == parent_id)
            used = {c.barcode_category_code for c in siblings if c.barcode_category_code}
            available = [f'{n:02d}' for n in range(1, 100) if f'{n:02d}' not in used]
            for category in siblings.filtered(lambda c: not c.barcode_category_code):
                if not available:
                    raise UserError(_(
                        'No hay códigos de 2 dígitos disponibles bajo la categoría padre %(parent)s.'
                    ) % {'parent': category.parent_id.complete_name or _('Raíz')})
                category.write({'barcode_category_code': available.pop(0)})
                assigned += 1
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Categorías'),
                'message': _('%(count)s códigos de categoría fueron asignados.') % {'count': assigned},
                'type': 'success',
                'sticky': False,
            },
        }

    def action_open_bulk_wizard(self):
        self.ensure_one()
        return {
            'name': _('Generar códigos de barras faltantes'),
            'type': 'ir.actions.act_window',
            'res_model': 'barcode.bulk.generator.rl',
            'view_mode': 'form',
            'target': 'new',
            'context': {'default_config_id': self.id},
        }

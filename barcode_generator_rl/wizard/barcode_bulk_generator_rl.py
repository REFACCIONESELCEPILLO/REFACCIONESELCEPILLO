# -*- coding: utf-8 -*-
import html
import logging
import time

from psycopg2 import InterfaceError, OperationalError

from odoo import api, fields, models, _
from odoo.exceptions import UserError
from odoo.tools import SQL

from ..models.barcode_utils import CONFIG_BARCODE_SELECTION_MAP

_logger = logging.getLogger(__name__)


class BarcodeBulkGeneratorRl(models.Model):
    _name = 'barcode.bulk.generator.rl'
    _description = 'Generación masiva de códigos de barras faltantes'
    _rec_name = 'config_id'
    _order = 'id desc'

    state = fields.Selection([
        ('draft', 'Sin iniciar'),
        ('queued', 'En espera'),
        ('running', 'En proceso'),
        ('done', 'Terminado'),
        ('failed', 'Requiere atención'),
    ], string='Estado del proceso', default='draft', required=True, readonly=True, index=True, copy=False)
    company_id = fields.Many2one(related='config_id.company_id', store=True, index=True)
    max_product_id = fields.Integer(string='Último producto incluido', readonly=True, copy=False)
    total_to_process = fields.Integer(string='Productos incluidos', readonly=True, copy=False)
    pending_count = fields.Integer(string='Pendientes de procesar', readonly=True, copy=False)
    progress = fields.Float(string='Avance', compute='_compute_progress')
    failure_message = fields.Text(string='Motivo de la interrupción', readonly=True, copy=False)

    config_id = fields.Many2one('barcode.generator.config.rl', string='Configuración', required=True, domain=[('active', '=', True)])
    barcode_type = fields.Selection(CONFIG_BARCODE_SELECTION_MAP, string='Tipo de barcode', required=True)
    include_archived = fields.Boolean(string='Incluir productos archivados', default=False)
    generate_images = fields.Boolean(string='Generar imágenes', default=True)
    batch_size = fields.Integer(string='Tamaño de lote', default=500, required=True)

    total_products = fields.Integer(string='Productos/variantes encontrados', compute='_compute_counts')
    with_barcode = fields.Integer(string='Ya tienen barcode', compute='_compute_counts')
    without_barcode = fields.Integer(string='Sin barcode', compute='_compute_counts')

    last_product_id = fields.Integer(string='Último producto procesado', readonly=True)
    has_more = fields.Boolean(string='Hay productos pendientes', readonly=True)
    error_details = fields.Json(string='Detalle de errores', readonly=True, default=list)
    generation_done = fields.Boolean(readonly=True)
    generated_count = fields.Integer(string='Generados', readonly=True)
    skipped_count = fields.Integer(string='Sin barcode al terminar', readonly=True)
    error_count = fields.Integer(string='Omitidos / con error', readonly=True)
    result_html = fields.Html(string='Resultado', readonly=True, sanitize=False)

    @api.depends('state', 'total_to_process', 'pending_count')
    def _compute_progress(self):
        for job in self:
            if job.state == 'done':
                job.progress = 100.0
            elif job.total_to_process:
                processed = job.total_to_process - job.pending_count
                job.progress = min(99.99, max(0.0, 100.0 * processed / job.total_to_process))
            else:
                job.progress = 0.0

    def write(self, vals):
        settings = {'config_id', 'barcode_type', 'include_archived', 'generate_images', 'batch_size'}
        if settings.intersection(vals) and any(job.state != 'draft' for job in self):
            raise UserError(_('No puede cambiar los parámetros de un proceso iniciado. Cree una nueva ejecución.'))
        return super().write(vals)

    def unlink(self):
        if any(job.state in ('queued', 'running') for job in self):
            raise UserError(_('No puede eliminar una generación que está en espera o en proceso.'))
        return super().unlink()

    def copy(self, default=None):
        raise UserError(_('Cree una nueva ejecución desde Generar código de barras por lotes.'))

    def _progress_action(self):
        return {
            'name': _('Generación de códigos de barras'),
            'type': 'ir.actions.act_window',
            'res_model': self._name,
            'res_id': self.id,
            'view_mode': 'form',
            'target': 'new',
        }

    def action_generate_missing(self):
        """Enqueue once; the cron owns processing and transaction boundaries."""
        self.ensure_one()
        self.check_access('write')
        self.env.cr.execute(SQL('SELECT id FROM %s WHERE id = %s FOR UPDATE',
                                SQL.identifier(self._table), self.id))
        self.invalidate_recordset()
        if self.state in ('queued', 'running', 'done'):
            return self._progress_action()
        self.config_id.sudo()._validate_structure(self.barcode_type)
        if self.state == 'draft':
            Product = self._product_model()
            domain = self._base_domain() + [('barcode', '=', False), ('id', '>', self.last_product_id)]
            last = Product.search(domain, order='id desc', limit=1)
            maximum = last.id if last else self.last_product_id
            pending = Product.search_count(domain + [('id', '<=', maximum)])
            self.write({
                'max_product_id': maximum,
                'total_to_process': pending + self.generated_count + self.error_count,
                'pending_count': pending,
            })
        self.write({'state': 'queued', 'failure_message': False})
        self.env.ref('barcode_generator_rl.ir_cron_generate_barcodes')._trigger()
        return self._progress_action()

    @api.model
    def _cron_generate_missing(self):
        """Odoo 18 commits each callback and reschedules remaining batches."""
        job = self.search([('state', 'in', ('queued', 'running'))], order='id', limit=1)
        if job:
            try:
                with self.env.cr.savepoint():
                    job.with_company(job.company_id)._process_batch()
            except (InterfaceError, OperationalError):
                raise
            except Exception as exc:
                _logger.exception('Background barcode generation failed for job %s', job.id)
                job.write({'state': 'failed', 'failure_message': str(exc)})
        remaining = self.search_count([('state', 'in', ('queued', 'running'))])
        self.env['ir.cron']._notify_progress(done=int(bool(job)), remaining=remaining)

    @api.model
    def default_get(self, fields_list):
        vals = super().default_get(fields_list)
        config_id = vals.get('config_id') or self.env.context.get('default_config_id')
        if not config_id:
            config = self.env['barcode.generator.config.rl'].sudo().search([
                ('company_id', '=', self.env.company.id), ('active', '=', True),
            ], limit=1)
            config_id = config.id
            if config_id:
                vals['config_id'] = config_id
        if config_id:
            config = self.env['barcode.generator.config.rl'].browse(config_id)
            vals.setdefault('barcode_type', config.default_barcode_type)
            vals.setdefault('generate_images', config.generate_image)
        return vals

    def _base_domain(self):
        self.ensure_one()
        return [('company_id', 'in', [False, self.config_id.company_id.id])]

    def _product_model(self):
        return self.env['product.product'].sudo().with_context(active_test=not self.include_archived)

    @api.depends('config_id', 'include_archived')
    def _compute_counts(self):
        for wizard in self:
            if not wizard.config_id:
                wizard.total_products = wizard.with_barcode = wizard.without_barcode = 0
                continue
            Product = wizard._product_model()
            base = wizard._base_domain()
            total = Product.search_count(base)
            missing = Product.search_count(base + [('barcode', '=', False)])
            wizard.total_products = total
            wizard.without_barcode = missing
            wizard.with_barcode = total - missing

    @api.constrains('batch_size')
    def _check_batch_size(self):
        for wizard in self:
            if wizard.batch_size < 50 or wizard.batch_size > 2000:
                from odoo.exceptions import ValidationError
                raise ValidationError(_('El tamaño de lote debe estar entre 50 y 2,000.'))

    def _process_batch(self):
        self.ensure_one()
        if self.state not in ('queued', 'running'):
            return
        config = self.config_id.sudo()
        config._validate_structure(self.barcode_type)
        Product = self._product_model()
        base_domain = self._base_domain() + [('barcode', '=', False), ('id', '<=', self.max_product_id)]

        # Odoo may call up to ten cron batches in one worker run. A short
        # budget leaves room for auditing, image rendering and final flushes.
        deadline = time.monotonic() + 5
        generated = self.generated_count
        errors = list(self.error_details or [])
        error_count = self.error_count
        last_id = self.last_product_id

        batch = Product.search(base_domain + [('id', '>', last_id)], order='id', limit=self.batch_size)
        for product in batch:
            product_name = product.display_name
            try:
                with self.env.cr.savepoint():
                    config.generate_for_product(
                        product,
                        barcode_type=self.barcode_type,
                        generate_image=self.generate_images,
                    )
                generated += 1
            except (InterfaceError, OperationalError):
                # Connection failures and retryable transaction errors must
                # reach Odoo's transaction handler, not become skipped products.
                raise
            except Exception as exc:
                _logger.warning('Bulk barcode skipped product %s: %s', product.id, exc)
                error_count += 1
                if len(errors) < 100:
                    errors.append((product_name, str(exc)))
            last_id = product.id
            if time.monotonic() >= deadline:
                break

        pending = Product.search_count(base_domain + [('id', '>', last_id)])
        has_more = bool(pending)
        # Recount after processing; this naturally includes records skipped due to errors.
        remaining = Product.search_count(base_domain)
        escaped_rows = ''.join(
            '<li><b>%s</b>: %s</li>' % (html.escape(name or ''), html.escape(message or ''))
            for name, message in errors[:100]
        )
        more = error_count - len(errors)
        if more > 0:
            escaped_rows += '<li>... y %s errores adicionales.</li>' % more

        result = f'''
            <div>
              <h3>Resultado de generación masiva</h3>
              <ul>
                <li><b>Generados:</b> {generated}</li>
                <li><b>Sin barcode al terminar:</b> {remaining}</li>
                <li><b>Omitidos / con error:</b> {error_count}</li>
              </ul>
        '''
        if has_more:
            result += '<p>La generación continúa automáticamente en segundo plano. Puede cerrar esta ventana.</p>'
        else:
            result += '<p>Proceso terminado. Los productos omitidos se muestran en el detalle de errores.</p>'
        if errors:
            result += '<p><b>Detalle (máximo 100):</b></p><ul>%s</ul>' % escaped_rows
        result += '</div>'

        self.write({
            'generation_done': True,
            'state': 'running' if has_more else 'done',
            'pending_count': pending,
            'last_product_id': last_id,
            'has_more': has_more,
            'error_details': errors,
            'generated_count': generated,
            'skipped_count': remaining,
            'error_count': error_count,
            'result_html': result,
        })
        return self._progress_action()

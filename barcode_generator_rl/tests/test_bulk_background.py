from unittest.mock import patch

from psycopg2 import InterfaceError

from odoo.exceptions import UserError
from odoo.tests import TransactionCase, tagged


@tagged('post_install', '-at_install')
class TestBulkBackground(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company = cls.env['res.company'].create({'name': 'Barcode background test'})
        cls.config = cls.env['barcode.generator.config.rl'].create({
            'name': 'Background test', 'company_id': cls.company.id,
            'category_levels': '0', 'company_prefix': '7', 'generate_image': False,
        })
        cls.products = cls.env['product.product'].create([
            {'name': 'Background %s' % index, 'company_id': cls.company.id}
            for index in range(3)
        ])
        cls.Job = cls.env['barcode.bulk.generator.rl']
        cls.job = cls.Job.create({
            'config_id': cls.config.id, 'barcode_type': 'code128',
            'generate_images': False, 'batch_size': 50,
        })

    def setUp(self):
        super().setUp()
        # Isolate this run from demo/shared products in the test database.
        scope = patch.object(type(self.Job), '_base_domain', return_value=[('id', 'in', self.products.ids)])
        scope.start()
        self.addCleanup(scope.stop)
        trigger = patch.object(type(self.env['ir.cron']), '_trigger')
        self.trigger = trigger.start()
        self.addCleanup(trigger.stop)

    def test_enqueue_is_idempotent_and_does_not_generate_in_http(self):
        self.job.action_generate_missing()
        self.job.action_generate_missing()
        self.assertEqual(self.job.state, 'queued')
        self.assertEqual(self.job.pending_count, 3)
        self.assertEqual(self.job.progress, 0)
        self.assertFalse(any(self.products.mapped('barcode')))
        self.trigger.assert_called_once()
        self.assertFalse(self.Job._transient)

    def test_cron_continues_and_reaches_full_progress(self):
        self.job.action_generate_missing()
        with patch('odoo.addons.barcode_generator_rl.wizard.barcode_bulk_generator_rl.time.monotonic',
                   side_effect=[0, 6] * 3), \
             patch.object(type(self.Job), 'search', return_value=self.job), \
             patch.object(type(self.env['ir.cron']), '_notify_progress') as notify:
            for count in range(1, 4):
                self.Job._cron_generate_missing()
                self.assertEqual(self.job.generated_count, count)
                self.assertEqual(self.job.pending_count, 3 - count)
                self.assertAlmostEqual(self.job.progress, count * 100 / 3)
            self.assertEqual(self.job.state, 'done')
            self.assertEqual(notify.call_args.kwargs['remaining'], 0)
        self.assertTrue(all(self.products.mapped('barcode')))

    def test_product_errors_do_not_block_following_products(self):
        self.job.action_generate_missing()
        original = type(self.config).generate_for_product
        bad_id = self.products[0].id
        def generate(config, product, **kwargs):
            if product.id == bad_id:
                raise UserError('<Categoría sin código>')
            return original(config, product, **kwargs)
        with patch.object(type(self.config), 'generate_for_product', generate), \
             patch('odoo.addons.barcode_generator_rl.wizard.barcode_bulk_generator_rl.time.monotonic', return_value=0):
            self.job._process_batch()
        self.assertEqual(self.job.state, 'done')
        self.assertEqual(self.job.error_count, 1)
        self.assertEqual(self.job.generated_count, 2)
        self.assertEqual(self.job.progress, 100)
        self.assertIn('&lt;Categoría sin código&gt;', self.job.result_html)

    def test_connection_failure_keeps_checkpoint(self):
        self.job.action_generate_missing()
        with patch.object(type(self.config), 'generate_for_product', side_effect=InterfaceError('closed')):
            with self.assertRaises(InterfaceError):
                self.job._process_batch()
        self.assertEqual(self.job.last_product_id, 0)
        self.assertEqual(self.job.error_count, 0)
        self.assertFalse(any(self.products.mapped('barcode')))

    def test_running_settings_and_deletion_are_protected(self):
        self.job.action_generate_missing()
        with self.assertRaises(UserError):
            self.job.write({'generate_images': True})
        with self.assertRaises(UserError):
            self.job.unlink()

    def test_fatal_error_is_visible_and_retry_preserves_checkpoint(self):
        self.job.action_generate_missing()
        with patch.object(type(self.Job), 'search', return_value=self.job), \
             patch.object(type(self.Job), '_process_batch', side_effect=UserError('Revisar configuración')):
            self.Job._cron_generate_missing()
        self.assertEqual(self.job.state, 'failed')
        self.assertIn('Revisar configuración', self.job.failure_message)
        self.job.action_generate_missing()
        self.assertEqual(self.job.state, 'queued')
        self.assertEqual(self.job.last_product_id, 0)
        self.assertFalse(self.job.failure_message)

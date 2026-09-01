from datetime import timedelta

from odoo import fields
from odoo.exceptions import UserError
from odoo.fields import Command
from odoo.tests import tagged
from odoo.addons.account.tests.common import AccountTestInvoicingCommon


@tagged('post_install', '-at_install')
class TestFsmFlows(AccountTestInvoicingCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env.user.group_ids += (
            cls.env.ref('hr.group_hr_manager')
            + cls.env.ref('al_field_service.group_fsm_manager')
        )
        for key in ('mail_assigned', 'mail_planned', 'mail_started', 'mail_done', 'mail_installation'):
            cls.env['ir.config_parameter'].sudo().set_param('al_field_service.%s' % key, 'False')
        cls.partner = cls.env['res.partner'].create({
            'name': 'Site Customer',
            'email': 'site@example.com',
            'phone': '555-0100',
        })
        cls.labor = cls.env['product.product'].create({
            'name': 'Field Labor',
            'type': 'service',
            'list_price': 100.0,
            'invoice_policy': 'order',
        })
        cls.part = cls.env['product.product'].create({
            'name': 'Replacement Fan',
            'type': 'consu',
            'is_storable': True,
            'list_price': 50.0,
            'invoice_policy': 'order',
        })
        cls.tech_user = cls.env['res.users'].create({
            'name': 'FSM Technician',
            'login': 'fsm_tech_user',
            'email': 'fsm.tech@example.com',
            'group_ids': [Command.set([
                cls.env.ref('al_field_service.group_fsm_manager').id,
                cls.env.ref('base.group_user').id,
            ])],
        })
        cls.employee = cls.env['hr.employee'].sudo().create({
            'name': 'Tech One',
            'user_id': cls.tech_user.id,
            'hourly_cost': 80.0,
        })
        cls.team = cls.env['fsm.team'].create({
            'name': 'Field Team A',
            'manager_id': cls.employee.id,
            'member_ids': [Command.set(cls.employee.ids)],
            'first_response_sla': 2.0,
            'resolution_sla': 24.0,
            'escalation_user_id': cls.env.user.id,
            'invoicing_policy': 'manual',
        })
        cls.location = cls.env['fsm.location'].create({
            'name': 'Plant North',
            'partner_id': cls.partner.id,
            'city': 'Austin',
            'phone': '555-0100',
        })
        cls.project = cls.env['project.project'].create({
            'name': 'FSM Contract',
            'is_fsm': True,
            'partner_id': cls.partner.id,
            'user_id': cls.env.user.id,
            'fsm_service_product_id': cls.labor.id,
            'allocated_hours': 8.0,
            'fsm_service_line_ids': [Command.create({
                'employee_id': cls.employee.id,
                'hourly_cost': 90.0,
            })],
        })
        cls.checklist = cls.env['fsm.checklist.template'].create({
            'name': 'Close-out',
            'line_ids': [
                Command.create({'name': 'Safety', 'is_mandatory': True}),
                Command.create({'name': 'Cleanup', 'is_mandatory': True}),
            ],
        })
        cls.worksheet = cls.env['fsm.worksheet.template'].create({
            'name': 'Visit notes',
            'body': '<p>Inspected unit.</p>',
        })

    def _order_vals(self, **extra):
        vals = {
            'partner_id': self.partner.id,
            'team_id': self.team.id,
            'project_id': self.project.id,
            'location_id': self.location.id,
            'technician_ids': [Command.set(self.employee.ids)],
            'supervisor_id': self.employee.id,
            'checklist_template_id': self.checklist.id,
            'worksheet_template_id': self.worksheet.id,
            'requested_date': fields.Datetime.now(),
            'allocated_hours': 8.0,
        }
        vals.update(extra)
        return vals

    def test_sequence_and_templates(self):
        order = self.env['fsm.order'].create(self._order_vals())
        self.assertTrue(order.name.startswith('FSM/'))
        self.assertEqual(len(order.checklist_line_ids), 2)
        self.assertTrue(order.worksheet_html)
        self.assertEqual(order.sla_status, 'on_track')
        self.assertEqual(order.supervisor_id, self.employee)

    def test_project_onchange_rates(self):
        order = self.env['fsm.order'].new({'project_id': self.project.id, 'partner_id': self.partner.id})
        order._onchange_project_id()
        self.assertEqual(order.service_product_id, self.labor)
        self.assertEqual(order.allocated_hours, 8.0)

    def test_cannot_done_without_checklist_and_signature(self):
        order = self.env['fsm.order'].create(self._order_vals())
        with self.assertRaises(UserError):
            order.action_mark_done()
        order.checklist_line_ids.write({'is_done': True})
        with self.assertRaises(UserError):
            order.action_mark_done()

    def test_plan_start_stop_and_done(self):
        order = self.env['fsm.order'].create(self._order_vals())
        order.action_plan()
        self.assertEqual(order.state, 'planned')
        self.assertTrue(order.calendar_event_id)
        order.action_start()
        self.assertEqual(order.state, 'in_progress')
        self.assertTrue(order.actual_date_begin)
        self.assertTrue(order.first_response_at)
        self.assertTrue(order.is_timer_running)
        order.action_stop()
        self.assertFalse(order.is_timer_running)
        self.assertTrue(order.timesheet_ids)
        self.assertGreater(order.spent_hours, 0)
        order.checklist_line_ids.write({'is_done': True})
        order.write({'signature': b'iVBORw0KGgo=', 'signed_by': 'Site Manager'})
        order.action_confirm_signature()
        order.action_mark_done()
        self.assertEqual(order.state, 'done')
        self.assertTrue(order.actual_date_end)

    def test_mark_response(self):
        order = self.env['fsm.order'].create(self._order_vals())
        order.action_mark_response()
        self.assertTrue(order.first_response_at)

    def test_sla_breach_and_cron(self):
        order = self.env['fsm.order'].create(self._order_vals(
            requested_date=fields.Datetime.now() - timedelta(hours=30),
        ))
        order.invalidate_recordset(['sla_status', 'is_escalated'])
        order._compute_sla()
        self.assertEqual(order.sla_status, 'breached')
        self.env['fsm.order']._cron_update_sla()
        self.assertTrue(order.is_escalated)
        self.assertTrue(order.activity_ids)

    def test_quotation_invoice_and_labor_lines(self):
        order = self.env['fsm.order'].create(self._order_vals())
        order.write({
            'timesheet_ids': [Command.create({
                'employee_id': self.employee.id,
                'hours': 2.0,
                'hourly_cost': 90.0,
                'description': 'Repair',
            })],
            'material_line_ids': [Command.create({
                'product_id': self.part.id,
                'name': self.part.name,
                'product_uom_qty': 3.0,
                'product_uom_id': self.part.uom_id.id,
                'price_unit': 50.0,
            })],
        })
        self.assertEqual(order.labor_amount, 180.0)
        self.assertEqual(order.material_amount, 150.0)
        self.assertEqual(order.total_amount, 330.0)
        order.action_create_quotation()
        self.assertTrue(order.sale_id)
        self.assertEqual(len(order.sale_id.order_line), 2)
        self.assertTrue(order.sale_id.order_line.filtered(lambda l: l.fsm_line_type == 'labor'))
        self.assertTrue(order.sale_id.order_line.filtered(lambda l: l.fsm_line_type == 'material'))
        order.sale_id.action_confirm()
        wizard = self.env['fsm.create.invoice'].create({
            'order_id': order.id,
            'sale_id': order.sale_id.id,
            'advance_payment_method': 'delivered',
        })
        wizard.action_create_invoices()
        self.assertTrue(order.invoice_ids)
        self.assertTrue(order.invoice_ids.fsm_order_id)

    def test_down_payment_wizard(self):
        order = self.env['fsm.order'].create(self._order_vals(service_product_id=self.labor.id, service_qty=1))
        order.action_create_quotation()
        wizard = self.env['fsm.create.invoice'].create({
            'order_id': order.id,
            'sale_id': order.sale_id.id,
            'advance_payment_method': 'percentage',
            'amount': 30.0,
        })
        wizard.action_create_invoices()
        self.assertTrue(order.sale_id.invoice_ids)

    def test_delivery(self):
        order = self.env['fsm.order'].create(self._order_vals())
        order.write({
            'material_line_ids': [Command.create({
                'product_id': self.part.id,
                'name': self.part.name,
                'product_uom_qty': 1.0,
                'product_uom_id': self.part.uom_id.id,
                'price_unit': 50.0,
            })],
        })
        order.action_create_delivery()
        self.assertEqual(order.picking_count, 1)

    def test_crm_and_sale_origin(self):
        lead = self.env['crm.lead'].create({
            'name': 'Broken chiller',
            'partner_id': self.partner.id,
            'type': 'opportunity',
        })
        action = lead.action_create_fsm_order()
        order = self.env['fsm.order'].browse(action['res_id'])
        self.assertEqual(order.source, 'crm')
        self.assertEqual(order.lead_id, lead)
        so = self.env['sale.order'].create({
            'partner_id': self.partner.id,
            'order_line': [Command.create({'product_id': self.labor.id, 'product_uom_qty': 4})],
        })
        action = so.action_create_fsm_order()
        so_order = self.env['fsm.order'].browse(action['res_id'])
        self.assertEqual(so_order.source, 'sale')
        self.assertEqual(so_order.sale_id, so)

    def test_maintenance_generation(self):
        plan = self.env['fsm.maintenance.plan'].create({
            'name': 'Quarterly PM',
            'partner_id': self.partner.id,
            'location_id': self.location.id,
            'team_id': self.team.id,
            'project_id': self.project.id,
            'interval': 1,
            'interval_unit': 'months',
            'next_date': fields.Date.today(),
            'checklist_template_id': self.checklist.id,
        })
        order = plan._generate_order()
        self.assertTrue(order.is_preventive)
        self.assertEqual(order.source, 'maintenance')
        self.assertGreater(plan.next_date, fields.Date.today())

    def test_sign_wizard_and_subtask(self):
        order = self.env['fsm.order'].create(self._order_vals())
        wiz = self.env['fsm.sign.report'].create({
            'order_id': order.id,
            'signed_by': 'Anita Oliver',
            'signature': b'abcd',
        })
        wiz.action_sign()
        self.assertTrue(order.signature_confirmed)
        child = self.env['fsm.order'].create(self._order_vals(parent_id=order.id, name='Follow-up visit'))
        self.assertEqual(order.child_count, 1)
        self.assertEqual(child.parent_id, order)

    def test_equipment_and_location_counts(self):
        eq = self.env['fsm.equipment'].create({
            'name': 'AHU-1',
            'partner_id': self.partner.id,
            'location_id': self.location.id,
            'warranty_end': fields.Date.today(),
        })
        self.assertTrue(eq.code.startswith('EQ/'))
        self.assertTrue(eq.under_warranty)
        order = self.env['fsm.order'].create(self._order_vals(equipment_id=eq.id))
        self.assertEqual(eq.order_count, 1)
        self.assertEqual(self.location.order_count, 1)
        self.assertTrue(self.location.map_url)

    def test_reset_and_cancel(self):
        order = self.env['fsm.order'].create(self._order_vals())
        order.action_plan()
        order.action_cancel()
        self.assertEqual(order.state, 'cancelled')
        order.action_reset_draft()
        self.assertEqual(order.state, 'draft')

    def test_close_gates_respect_settings(self):
        ICP = self.env['ir.config_parameter'].sudo()
        ICP.set_param('al_field_service.require_checklist', 'False')
        ICP.set_param('al_field_service.require_signature', 'False')
        order = self.env['fsm.order'].create(self._order_vals())
        order.action_mark_done()
        self.assertEqual(order.state, 'done')

    def test_auto_so_and_update(self):
        self.team.invoicing_policy = 'auto'
        order = self.env['fsm.order'].create(self._order_vals())
        order.write({
            'material_line_ids': [Command.create({
                'product_id': self.part.id,
                'name': self.part.name,
                'product_uom_qty': 2.0,
                'product_uom_id': self.part.uom_id.id,
                'price_unit': 50.0,
            })],
        })
        self.assertTrue(order.sale_id)
        self.assertEqual(len(order.sale_id.order_line), 1)
        order.write({
            'timesheet_ids': [Command.create({
                'employee_id': self.employee.id,
                'hours': 1.0,
                'hourly_cost': 90.0,
                'description': 'On site',
            })],
        })
        self.assertGreaterEqual(len(order.sale_id.order_line), 2)
        self.assertTrue(order.sale_id.order_line.filtered(lambda l: l.fsm_line_type == 'labor'))

    def test_default_project_and_labor(self):
        ICP = self.env['ir.config_parameter'].sudo()
        ICP.set_param('al_field_service.default_project_id', str(self.project.id))
        ICP.set_param('al_field_service.labor_product_id', str(self.labor.id))
        order = self.env['fsm.order'].create({'partner_id': self.partner.id})
        self.assertEqual(order.project_id, self.project)
        self.assertEqual(order.service_product_id, self.labor)

    def test_favorite_skill_warning_and_documents(self):
        skill = self.env['fsm.skill'].create({'name': 'HVAC Cert'})
        order = self.env['fsm.order'].create(self._order_vals(skill_ids=[Command.set(skill.ids)]))
        self.assertTrue(order.skill_warning)
        self.employee.fsm_skill_ids = skill
        order.invalidate_recordset(['skill_warning'])
        self.assertFalse(order.skill_warning)
        order.is_favorite = True
        self.assertIn(self.env.user, order.favorite_user_ids)
        action = order.action_view_attachments()
        self.assertEqual(action['res_model'], 'ir.attachment')
        self.assertTrue(order.action_open_map()['url'])

    def test_sale_confirm_creates_task(self):
        self.labor.fsm_create_task = True
        so = self.env['sale.order'].create({
            'partner_id': self.partner.id,
            'order_line': [Command.create({'product_id': self.labor.id, 'product_uom_qty': 3})],
        })
        so.action_confirm()
        self.assertEqual(so.fsm_order_count, 1)
        order = so.fsm_order_ids
        self.assertEqual(order.source, 'sale')
        self.assertEqual(order.sale_line_id.product_id, self.labor)
        self.assertEqual(order.allocated_hours, 3.0)

    def test_product_catalog_and_template(self):
        self.part.fsm_ok = True
        order = self.env['fsm.order'].create(self._order_vals())
        order._update_order_line_info(self.part.id, 2)
        self.assertEqual(order.material_count, 1)
        self.assertEqual(order.material_line_ids.product_uom_qty, 2)
        action = order.action_add_from_catalog()
        self.assertEqual(action['res_model'], 'product.product')
        tpl = self.env['fsm.order.template'].create({
            'name': 'Chiller repair',
            'job_type': 'repair',
            'allocated_hours': 4.0,
            'checklist_template_id': self.checklist.id,
        })
        order.template_id = tpl.id
        order._onchange_template_id()
        self.assertEqual(order.allocated_hours, 4.0)

    def test_gantt_map_and_navigate(self):
        order = self.env['fsm.order'].create(self._order_vals(
            planned_date_begin=fields.Datetime.now(),
            planned_date_end=fields.Datetime.now() + timedelta(hours=2),
        ))
        gantt = self.env['fsm.order'].get_gantt_payload()
        self.assertTrue(gantt['days'])
        mapped = self.env['fsm.order'].get_map_payload()
        self.assertTrue(mapped['pins'])
        nav = order.action_navigate()
        self.assertIn('google.com/maps', nav['url'])
        itinerary = order.action_google_itinerary()
        self.assertIn('google.com/maps/dir', itinerary['url'])

    def test_technician_signature(self):
        order = self.env['fsm.order'].create(self._order_vals())
        with self.assertRaises(UserError):
            order.action_confirm_technician_signature()
        order.write({'technician_signature': b'abcd', 'technician_signed_by': 'Tech One'})
        order.action_confirm_technician_signature()
        self.assertTrue(order.technician_signed_on)

    def test_installation_serial_technician_warranty(self):
        self.employee.fsm_grade = 'a'
        ICP = self.env['ir.config_parameter'].sudo()
        ICP.set_param('al_field_service.require_checklist', 'False')
        ICP.set_param('al_field_service.require_signature', 'False')
        order = self.env['fsm.order'].create(self._order_vals(
            job_type='install',
            serial_number='SN-AASHA-001',
            model_number='DISP-200',
            manufacturer='Aasha',
            warranty_months=18,
            collected_notes='<p>Tank commissioned, 200L.</p>',
        ))
        order.action_plan()
        order.action_start()
        self.assertEqual(self.employee.fsm_status, 'busy')
        order.action_mark_done()
        self.assertTrue(order.installation_id)
        inst = order.installation_id
        self.assertEqual(inst.serial, 'SN-AASHA-001')
        self.assertEqual(inst.technician_id, self.employee)
        self.assertEqual(inst.technician_grade, 'a')
        self.assertEqual(order.equipment_id.installer_id, self.employee)
        self.assertEqual(order.equipment_id.serial, 'SN-AASHA-001')
        self.assertTrue(order.equipment_id.under_warranty)
        self.assertEqual(self.employee.fsm_status, 'idle')
        self.assertEqual(self.employee.fsm_serial_count, 1)

    def test_idle_busy_and_grade(self):
        self.employee.fsm_grade = 'b'
        self.assertEqual(self.employee.fsm_status, 'idle')
        ICP = self.env['ir.config_parameter'].sudo()
        ICP.set_param('al_field_service.require_checklist', 'False')
        ICP.set_param('al_field_service.require_signature', 'False')
        order = self.env['fsm.order'].create(self._order_vals())
        order.action_start()
        self.assertEqual(self.employee.fsm_status, 'busy')
        order.action_mark_done()
        self.assertEqual(self.employee.fsm_status, 'idle')
        self.employee.fsm_status_override = 'off'
        self.employee._compute_fsm_status()
        self.assertEqual(self.employee.fsm_status, 'off')

    def test_warranty_reminder_cron(self):
        eq = self.env['fsm.equipment'].create({
            'name': 'Pump-1',
            'partner_id': self.partner.id,
            'serial': 'SN-WARN-1',
            'installer_id': self.employee.id,
            'warranty_end': fields.Date.today(),
        })
        self.env['fsm.equipment']._cron_warranty_reminder()
        self.assertTrue(eq.warranty_reminder_sent)

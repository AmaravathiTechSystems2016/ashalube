from dateutil.relativedelta import relativedelta

from odoo import api, fields, models
from odoo.exceptions import UserError
from odoo.tools.translate import _


class FsmMaintenancePlan(models.Model):
    _name = 'fsm.maintenance.plan'
    _description = 'Preventive Maintenance Plan'
    _inherit = ['mail.thread']
    _order = 'name'
    _check_company_auto = True

    name = fields.Char(required=True, tracking=True)
    active = fields.Boolean(default=True)
    partner_id = fields.Many2one('res.partner', string='Customer', required=True)
    location_id = fields.Many2one('fsm.location')
    equipment_id = fields.Many2one('fsm.equipment')
    project_id = fields.Many2one('project.project', domain=[('is_fsm', '=', True)])
    team_id = fields.Many2one('fsm.team', required=True)
    worksheet_template_id = fields.Many2one('fsm.worksheet.template')
    checklist_template_id = fields.Many2one('fsm.checklist.template')
    interval = fields.Integer(default=1, required=True)
    interval_unit = fields.Selection(
        [('days', 'Days'), ('weeks', 'Weeks'), ('months', 'Months'), ('years', 'Years')],
        default='months',
        required=True,
    )
    next_date = fields.Date(required=True, tracking=True)
    last_generated_date = fields.Date(readonly=True)
    allocated_hours = fields.Float(default=2.0)
    company_id = fields.Many2one('res.company', default=lambda self: self.env.company)
    order_count = fields.Integer(compute='_compute_order_count')

    def _compute_order_count(self):
        data = self.env['fsm.order']._read_group(
            [('maintenance_plan_id', 'in', self.ids)],
            ['maintenance_plan_id'],
            ['__count'],
        )
        mapped = {plan.id: count for plan, count in data}
        for plan in self:
            plan.order_count = mapped.get(plan.id, 0)

    def _next_after(self, date_from):
        self.ensure_one()
        delta = {
            'days': relativedelta(days=self.interval),
            'weeks': relativedelta(weeks=self.interval),
            'months': relativedelta(months=self.interval),
            'years': relativedelta(years=self.interval),
        }[self.interval_unit]
        return date_from + delta

    def action_generate_order(self):
        orders = self.env['fsm.order']
        for plan in self:
            orders |= plan._generate_order()
        if not orders:
            raise UserError(_('No work order generated.'))
        action = {
            'type': 'ir.actions.act_window',
            'name': _('Preventive Work Orders'),
            'res_model': 'fsm.order',
            'view_mode': 'list,form',
            'domain': [('id', 'in', orders.ids)],
        }
        if len(orders) == 1:
            action.update({'view_mode': 'form', 'res_id': orders.id})
        return action

    def _generate_order(self):
        self.ensure_one()
        stage = self.env.ref('al_field_service.stage_draft', raise_if_not_found=False)
        order = self.env['fsm.order'].create({
            'name': _('%s — %s', self.name, self.next_date),
            'partner_id': self.partner_id.id,
            'location_id': self.location_id.id,
            'equipment_id': self.equipment_id.id,
            'project_id': self.project_id.id,
            'team_id': self.team_id.id,
            'is_preventive': True,
            'maintenance_plan_id': self.id,
            'job_type': 'preventive',
            'source': 'maintenance',
            'worksheet_template_id': self.worksheet_template_id.id,
            'checklist_template_id': self.checklist_template_id.id,
            'allocated_hours': self.allocated_hours,
            'requested_date': fields.Datetime.to_datetime(self.next_date) if self.next_date else False,
            'stage_id': stage.id if stage else False,
        })
        self.write({
            'last_generated_date': fields.Date.context_today(self),
            'next_date': self._next_after(self.next_date),
        })
        return order

    @api.model
    def _cron_generate_orders(self):
        today = fields.Date.context_today(self)
        plans = self.search([('active', '=', True), ('next_date', '<=', today)])
        for plan in plans:
            plan._generate_order()

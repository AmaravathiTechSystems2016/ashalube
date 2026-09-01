from collections import defaultdict
from datetime import timedelta
from urllib.parse import quote_plus

from odoo import api, fields, models
from odoo.exceptions import UserError, ValidationError
from odoo.fields import Command, Domain
from odoo.tools.translate import _


class FsmOrder(models.Model):
    _name = 'fsm.order'
    _description = 'Field Service Work Order'
    _inherit = ['portal.mixin', 'mail.activity.mixin', 'rating.mixin', 'product.catalog.mixin']
    _order = 'priority desc, planned_date_begin, id desc'
    _mail_post_access = 'read'
    _check_company_auto = True

    name = fields.Char(required=True, copy=False, default='New', tracking=True)
    color = fields.Integer()
    active = fields.Boolean(default=True)
    company_id = fields.Many2one('res.company', default=lambda self: self.env.company, required=True, index=True)
    currency_id = fields.Many2one(related='company_id.currency_id', store=True)
    priority = fields.Selection(
        [('0', 'Normal'), ('1', 'Low'), ('2', 'High')],
        default='0',
        index=True,
        tracking=True,
    )
    is_emergency = fields.Boolean(tracking=True)
    job_type = fields.Selection(
        [
            ('install', 'Installation'),
            ('repair', 'Repair'),
            ('inspection', 'Inspection'),
            ('preventive', 'Preventive'),
            ('emergency', 'Emergency'),
            ('survey', 'Survey'),
            ('other', 'Other'),
        ],
        default='repair',
        required=True,
        tracking=True,
    )
    source = fields.Selection(
        [
            ('manual', 'Manual'),
            ('crm', 'CRM'),
            ('sale', 'Sales Order'),
            ('phone', 'Phone'),
            ('email', 'Email'),
            ('portal', 'Customer Portal'),
            ('walk_in', 'Walk-in'),
            ('maintenance', 'Preventive Plan'),
        ],
        default='manual',
        required=True,
    )
    stage_id = fields.Many2one(
        'fsm.stage',
        default=lambda self: self.env.ref('al_field_service.stage_draft', raise_if_not_found=False),
        group_expand='_read_group_stage_ids',
        tracking=True,
        index=True,
        copy=False,
    )
    state = fields.Selection(related='stage_id.code', store=True, index=True)
    tag_ids = fields.Many2many('fsm.tag', string='Tags')
    skill_ids = fields.Many2many('fsm.skill', string='Required skills')

    team_id = fields.Many2one('fsm.team', tracking=True)
    project_id = fields.Many2one('project.project', domain=[('is_fsm', '=', True)], tracking=True)
    supervisor_id = fields.Many2one('hr.employee', tracking=True)
    technician_ids = fields.Many2many('hr.employee', 'fsm_order_technician_rel', 'order_id', 'employee_id', string='Technicians')
    user_ids = fields.Many2many('res.users', compute='_compute_user_ids', store=True, string='Assignees')

    is_preventive = fields.Boolean()
    maintenance_plan_id = fields.Many2one('fsm.maintenance.plan')
    equipment_id = fields.Many2one('fsm.equipment')
    serial_number = fields.Char('Serial Number')
    model_number = fields.Char()
    manufacturer = fields.Char()
    collected_notes = fields.Html('Collected information')
    photo_ids = fields.One2many('fsm.order.photo', 'order_id')
    installation_id = fields.Many2one('fsm.installation', copy=False)
    warranty_months = fields.Integer(default=12)
    warranty_type = fields.Selection(
        [
            ('standard', 'Standard'),
            ('extended', 'Extended'),
            ('parts', 'Parts only'),
            ('labor', 'Labor only'),
            ('comprehensive', 'Comprehensive'),
        ],
        default='standard',
    )
    checklist_template_id = fields.Many2one('fsm.checklist.template')
    worksheet_template_id = fields.Many2one('fsm.worksheet.template')
    template_id = fields.Many2one('fsm.order.template', string='Job Template')
    activity_plan_id = fields.Many2one(
        'mail.activity.plan',
        domain="[('res_model', '=', 'fsm.order')]",
    )

    sale_line_id = fields.Many2one('sale.order.line', string='Sales Order Item')
    sale_id = fields.Many2one('sale.order', string='Sale Order', tracking=True, copy=False)
    lead_id = fields.Many2one('crm.lead', string='Opportunity', copy=False)
    picking_ids = fields.One2many('stock.picking', 'fsm_order_id')
    picking_count = fields.Integer(compute='_compute_picking_count')
    invoice_ids = fields.Many2many('account.move', compute='_compute_invoice_ids')
    invoice_count = fields.Integer(compute='_compute_invoice_ids')
    calendar_event_id = fields.Many2one('calendar.event', copy=False)

    requested_date = fields.Datetime(tracking=True)
    planned_date_begin = fields.Datetime('Planned Start', tracking=True, index=True)
    planned_date_end = fields.Datetime('Planned End', tracking=True)
    allocated_hours = fields.Float(default=0.0)
    spent_hours = fields.Float(compute='_compute_hours', store=True)
    remaining_hours = fields.Float(compute='_compute_hours', store=True)
    duration_hours = fields.Float(compute='_compute_hours', store=True)
    travel_hours = fields.Float()
    actual_date_begin = fields.Datetime('Actual Start', readonly=True, copy=False)
    actual_date_end = fields.Datetime('Actual End', readonly=True, copy=False)
    timer_start = fields.Datetime(copy=False)
    is_timer_running = fields.Boolean(compute='_compute_is_timer_running')
    timer_elapsed = fields.Float(compute='_compute_is_timer_running')
    favorite_user_ids = fields.Many2many(
        'res.users', 'fsm_order_favorite_rel', 'order_id', 'user_id', copy=False,
    )
    is_favorite = fields.Boolean(compute='_compute_is_favorite', inverse='_inverse_is_favorite')
    skill_warning = fields.Char(compute='_compute_skill_warning')
    progress = fields.Float(compute='_compute_hours', store=True)
    progress_color = fields.Char(compute='_compute_hours', store=True)

    partner_id = fields.Many2one('res.partner', string='Customer', required=True, tracking=True)
    location_id = fields.Many2one('fsm.location', string='Service Location')
    contact_id = fields.Many2one('res.partner', string='Contact Person')
    phone = fields.Char()
    email = fields.Char()
    customer_po = fields.Char('Customer PO')
    preferred_window_start = fields.Datetime('Preferred from')
    preferred_window_end = fields.Datetime('Preferred to')
    map_url = fields.Char(related='location_id.map_url')

    sla_status = fields.Selection(
        [
            ('none', 'No SLA'),
            ('on_track', 'On Track'),
            ('at_risk', 'At Risk'),
            ('breached', 'Breached'),
        ],
        default='none',
        compute='_compute_sla',
        store=True,
        tracking=True,
    )
    first_response_at = fields.Datetime(readonly=True, copy=False)
    response_deadline = fields.Datetime(compute='_compute_sla', store=True)
    resolution_deadline = fields.Datetime(compute='_compute_sla', store=True)
    is_escalated = fields.Boolean(copy=False, tracking=True)

    description = fields.Html('Issue details')
    resolution_notes = fields.Html('Work performed')
    worksheet_html = fields.Html('Worksheet', sanitize=False)

    timesheet_ids = fields.One2many('fsm.timesheet', 'order_id')
    material_line_ids = fields.One2many('fsm.material.line', 'order_id')
    checklist_line_ids = fields.One2many('fsm.checklist.line', 'order_id')
    parent_id = fields.Many2one('fsm.order', string='Parent Order', index=True)
    child_ids = fields.One2many('fsm.order', 'parent_id', string='Sub-tasks')
    child_count = fields.Integer(compute='_compute_child_count')

    signature = fields.Binary(copy=False, attachment=True)
    signed_by = fields.Char(copy=False)
    signed_on = fields.Datetime(copy=False)
    signature_confirmed = fields.Boolean(copy=False)
    technician_signature = fields.Binary(copy=False, attachment=True)
    technician_signed_by = fields.Char(copy=False)
    technician_signed_on = fields.Datetime(copy=False)
    break_hours = fields.Float()
    check_in_latitude = fields.Float(digits=(10, 7))
    check_in_longitude = fields.Float(digits=(10, 7))
    is_worksheet_complete = fields.Boolean(compute='_compute_worksheet_complete')
    material_count = fields.Integer(compute='_compute_amounts', store=True)

    service_product_id = fields.Many2one('product.product', domain=[('type', '=', 'service')])
    service_qty = fields.Float(default=1.0)
    labor_amount = fields.Monetary(compute='_compute_amounts', store=True, currency_field='currency_id')
    material_amount = fields.Monetary(compute='_compute_amounts', store=True, currency_field='currency_id')
    total_amount = fields.Monetary(compute='_compute_amounts', store=True, currency_field='currency_id')
    material_qty_total = fields.Float(compute='_compute_amounts', store=True)

    warehouse_id = fields.Many2one('stock.warehouse')
    van_location_id = fields.Many2one('stock.location', string='Technician Stock Location (Van)')

    so_policy = fields.Selection(
        [('manual', 'Manual'), ('auto', 'Automatic')],
        compute='_compute_so_policy',
        string='Materials / Timesheets SO policy',
    )
    next_activity_hint = fields.Char(compute='_compute_next_activity')
    rating_request = fields.Boolean(default=True, string='Ask customer rating')

    def _compute_access_url(self):
        super()._compute_access_url()
        for order in self:
            order.access_url = f'/my/fsm/{order.id}'

    @api.model
    def _read_group_stage_ids(self, stages, domain):
        return self.env['fsm.stage'].search([('active', '=', True)])

    @api.depends('technician_ids.user_id', 'supervisor_id.user_id')
    def _compute_user_ids(self):
        for order in self:
            users = order.technician_ids.user_id | order.supervisor_id.user_id
            order.user_ids = users

    @api.depends('timer_start')
    def _compute_is_timer_running(self):
        now = fields.Datetime.now()
        for order in self:
            order.is_timer_running = bool(order.timer_start)
            if order.timer_start:
                order.timer_elapsed = (now - order.timer_start).total_seconds() / 3600.0
            else:
                order.timer_elapsed = 0.0

    @api.depends('favorite_user_ids')
    def _compute_is_favorite(self):
        uid = self.env.uid
        for order in self:
            order.is_favorite = uid in order.favorite_user_ids.ids

    def _inverse_is_favorite(self):
        for order in self:
            if order.is_favorite:
                order.favorite_user_ids = [Command.link(self.env.uid)]
            else:
                order.favorite_user_ids = [Command.unlink(self.env.uid)]

    @api.depends('team_id.invoicing_policy')
    def _compute_so_policy(self):
        default = self.env['ir.config_parameter'].sudo().get_param('al_field_service.so_policy', 'manual') or 'manual'
        for order in self:
            order.so_policy = order.team_id.invoicing_policy or default

    @api.depends('skill_ids', 'technician_ids', 'technician_ids.fsm_skill_ids', 'team_id.skill_ids')
    def _compute_skill_warning(self):
        for order in self:
            required = order.skill_ids
            if not required:
                order.skill_warning = False
                continue
            covered = order.technician_ids.mapped('fsm_skill_ids') | order.team_id.skill_ids
            missing = required - covered
            order.skill_warning = (
                _('Assigned technicians/team do not cover: %s', ', '.join(missing.mapped('name')))
                if missing else False
            )

    @api.depends('worksheet_html', 'signature_confirmed', 'state')
    def _compute_worksheet_complete(self):
        for order in self:
            order.is_worksheet_complete = bool(order.signature_confirmed) or (
                bool(order.worksheet_html) and order.state in ('in_progress', 'done')
            )

    @api.depends('child_ids')
    def _compute_child_count(self):
        for order in self:
            order.child_count = len(order.child_ids)

    @api.depends('picking_ids')
    def _compute_picking_count(self):
        for order in self:
            order.picking_count = len(order.picking_ids)

    @api.depends('sale_id', 'sale_id.invoice_ids')
    def _compute_invoice_ids(self):
        Invoice = self.env['account.move']
        linked = Invoice.search([('fsm_order_id', 'in', self.ids)])
        by_order = {}
        for move in linked:
            by_order.setdefault(move.fsm_order_id.id, Invoice)
            by_order[move.fsm_order_id.id] |= move
        for order in self:
            moves = order.sale_id.invoice_ids if order.sale_id else Invoice
            moves |= by_order.get(order.id, Invoice)
            order.invoice_ids = moves
            order.invoice_count = len(moves)

    @api.depends('activity_ids', 'activity_ids.summary', 'activity_ids.activity_type_id')
    def _compute_next_activity(self):
        for order in self:
            act = order.activity_ids[:1]
            order.next_activity_hint = act.summary or act.activity_type_id.name if act else False

    @api.depends(
        'timesheet_ids.hours', 'timesheet_ids.total_cost',
        'material_line_ids.price_subtotal', 'material_line_ids.product_uom_qty',
        'allocated_hours', 'planned_date_begin', 'planned_date_end',
        'actual_date_begin', 'actual_date_end', 'travel_hours',
    )
    def _compute_hours(self):
        for order in self:
            spent = sum(order.timesheet_ids.mapped('hours'))
            order.spent_hours = spent
            order.remaining_hours = order.allocated_hours - spent
            if order.actual_date_begin and order.actual_date_end:
                order.duration_hours = (order.actual_date_end - order.actual_date_begin).total_seconds() / 3600.0
            elif order.planned_date_begin and order.planned_date_end:
                order.duration_hours = (order.planned_date_end - order.planned_date_begin).total_seconds() / 3600.0
            else:
                order.duration_hours = 0.0
            if order.allocated_hours:
                order.progress = min(100.0, spent / order.allocated_hours * 100.0)
            else:
                order.progress = 100.0 if order.state == 'done' else 0.0
            if order.progress > 100 or (order.allocated_hours and spent > order.allocated_hours):
                order.progress_color = 'danger'
            elif order.progress >= 80:
                order.progress_color = 'warning'
            else:
                order.progress_color = 'success'

    @api.depends('timesheet_ids.total_cost', 'material_line_ids.price_subtotal')
    def _compute_amounts(self):
        for order in self:
            order.labor_amount = sum(order.timesheet_ids.mapped('total_cost'))
            order.material_amount = sum(order.material_line_ids.mapped('price_subtotal'))
            order.total_amount = order.labor_amount + order.material_amount
            order.material_qty_total = sum(order.material_line_ids.mapped('product_uom_qty'))
            order.material_count = len(order.material_line_ids)

    @api.depends(
        'team_id', 'team_id.first_response_sla', 'team_id.resolution_sla',
        'team_id.at_risk_ratio', 'requested_date', 'create_date',
        'first_response_at', 'actual_date_end', 'state',
    )
    def _compute_sla(self):
        now = fields.Datetime.now()
        for order in self:
            team = order.team_id
            if not team or (not team.first_response_sla and not team.resolution_sla):
                order.sla_status = 'none'
                order.response_deadline = False
                order.resolution_deadline = False
                continue
            start = order.requested_date or order.create_date or now
            order.response_deadline = start + timedelta(hours=team.first_response_sla or 0.0)
            order.resolution_deadline = start + timedelta(hours=team.resolution_sla or 0.0)
            if order.state in ('done', 'cancelled'):
                end = order.actual_date_end or now
                order.sla_status = 'breached' if order.resolution_deadline and end > order.resolution_deadline else 'on_track'
                continue
            if order.resolution_deadline and now > order.resolution_deadline:
                order.sla_status = 'breached'
            elif order.response_deadline and not order.first_response_at and now > order.response_deadline:
                order.sla_status = 'breached'
            else:
                window = (order.resolution_deadline - start).total_seconds() if order.resolution_deadline else 0
                remaining = (order.resolution_deadline - now).total_seconds() if order.resolution_deadline else 0
                ratio = team.at_risk_ratio or 0.25
                if window and remaining <= window * ratio:
                    order.sla_status = 'at_risk'
                else:
                    order.sla_status = 'on_track'

    @api.onchange('project_id')
    def _onchange_project_id(self):
        project = self.project_id
        if not project:
            return
        if project.partner_id and not self.partner_id:
            self.partner_id = project.partner_id
        if project.user_id:
            employee = self.env['hr.employee'].search([('user_id', '=', project.user_id.id)], limit=1)
            if employee:
                self.supervisor_id = employee
        if project.fsm_worksheet_template_id:
            self.worksheet_template_id = project.fsm_worksheet_template_id
        if project.fsm_service_product_id:
            self.service_product_id = project.fsm_service_product_id
        if project.allocated_hours and not self.allocated_hours:
            self.allocated_hours = project.allocated_hours

    @api.onchange('location_id')
    def _onchange_location_id(self):
        loc = self.location_id
        if not loc:
            return
        self.partner_id = loc.partner_id
        self.phone = loc.phone
        self.email = loc.email

    @api.onchange('partner_id')
    def _onchange_partner_id(self):
        if self.partner_id and not self.phone:
            self.phone = self.partner_id.phone
        if self.partner_id and not self.email:
            self.email = self.partner_id.email

    @api.onchange('equipment_id')
    def _onchange_equipment_id(self):
        eq = self.equipment_id
        if eq:
            self.partner_id = eq.partner_id
            self.location_id = eq.location_id
            self.serial_number = eq.serial
            self.model_number = eq.model_number
            self.manufacturer = eq.manufacturer

    @api.onchange('technician_ids')
    def _onchange_technician_ids(self):
        vans = self.technician_ids.mapped('fsm_van_location_id')
        if len(vans) == 1 and not self.van_location_id:
            self.van_location_id = vans

    @api.onchange('template_id')
    def _onchange_template_id(self):
        if self.template_id:
            self.update(self.template_id._prepare_order_vals())

    @api.onchange('checklist_template_id')
    def _onchange_checklist_template(self):
        if self.checklist_template_id:
            self.checklist_line_ids = [Command.clear()] + [
                Command.create({
                    'name': line.name,
                    'is_mandatory': line.is_mandatory,
                    'sequence': line.sequence,
                })
                for line in self.checklist_template_id.line_ids
            ]

    @api.onchange('worksheet_template_id')
    def _onchange_worksheet_template(self):
        if self.worksheet_template_id and not self.worksheet_html:
            self.worksheet_html = self.worksheet_template_id.body

    @api.onchange('sale_line_id')
    def _onchange_sale_line_id(self):
        line = self.sale_line_id
        if line:
            self.sale_id = line.order_id
            self.partner_id = line.order_id.partner_id
            self.service_product_id = line.product_id
            self.service_qty = line.product_uom_qty

    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)
        ICP = self.env['ir.config_parameter'].sudo()
        if 'project_id' in fields_list and not res.get('project_id'):
            project_id = int(ICP.get_param('al_field_service.default_project_id', '0') or 0)
            if project_id:
                res['project_id'] = project_id
        if 'service_product_id' in fields_list and not res.get('service_product_id'):
            product_id = int(ICP.get_param('al_field_service.labor_product_id', '0') or 0)
            if product_id:
                res['service_product_id'] = product_id
        return res

    @api.model_create_multi
    def create(self, vals_list):
        ICP = self.env['ir.config_parameter'].sudo()
        default_project = int(ICP.get_param('al_field_service.default_project_id', '0') or 0)
        default_labor = int(ICP.get_param('al_field_service.labor_product_id', '0') or 0)
        for vals in vals_list:
            if vals.get('name', 'New') == 'New':
                vals['name'] = self.env['ir.sequence'].next_by_code('fsm.order') or 'New'
            if default_project and not vals.get('project_id'):
                vals['project_id'] = default_project
            if default_labor and not vals.get('service_product_id'):
                vals['service_product_id'] = default_labor
        orders = super().create(vals_list)
        for order in orders:
            order._apply_templates_on_create()
            order.message_subscribe(partner_ids=order.partner_id.ids)
            if order.technician_ids:
                order._fsm_send_mail('mail_template_fsm_assigned')
        return orders

    def write(self, vals):
        old_techs = self.mapped('technician_ids') if 'technician_ids' in vals or 'stage_id' in vals else self.env['hr.employee']
        res = super().write(vals)
        if 'stage_id' in vals:
            for order in self:
                order._on_stage_change()
        if any(k in vals for k in ('timesheet_ids', 'material_line_ids', 'service_product_id', 'service_qty')):
            self._maybe_sync_sale()
        if 'technician_ids' in vals:
            for order in self.filtered('technician_ids'):
                order._fsm_send_mail('mail_template_fsm_assigned')
        if 'technician_ids' in vals or 'stage_id' in vals:
            (old_techs | self.mapped('technician_ids'))._compute_fsm_status()
        return res

    def _apply_templates_on_create(self):
        self.ensure_one()
        if self.checklist_template_id and not self.checklist_line_ids:
            self.checklist_line_ids = [
                Command.create({
                    'name': line.name,
                    'is_mandatory': line.is_mandatory,
                    'sequence': line.sequence,
                })
                for line in self.checklist_template_id.line_ids
            ]
        if self.worksheet_template_id and not self.worksheet_html:
            self.worksheet_html = self.worksheet_template_id.body
        if self.activity_plan_id:
            self._apply_activity_plan()

    def _apply_activity_plan(self):
        self.ensure_one()
        plan = self.activity_plan_id
        responsible = self.supervisor_id.user_id or self.env.user
        for tmpl in plan.template_ids:
            delay = tmpl.delay_count or 0
            date_deadline = fields.Date.context_today(self)
            if tmpl.delay_unit == 'days':
                date_deadline += timedelta(days=delay)
            elif tmpl.delay_unit == 'weeks':
                date_deadline += timedelta(weeks=delay)
            elif tmpl.delay_unit == 'months':
                date_deadline += timedelta(days=30 * delay)
            self.activity_schedule(
                act_type_xmlid=None,
                date_deadline=date_deadline,
                summary=tmpl.summary or tmpl.activity_type_id.name,
                user_id=responsible.id,
                activity_type_id=tmpl.activity_type_id.id,
            )

    def _on_stage_change(self):
        self.ensure_one()
        code = self.state
        now = fields.Datetime.now()
        vals = {}
        if code == 'in_progress' and not self.actual_date_begin:
            vals['actual_date_begin'] = now
        if code == 'done':
            self._check_can_done()
            vals['actual_date_end'] = now
            if self.timer_start:
                vals['timer_start'] = False
            if self.rating_request:
                self._send_rating_request()
        if code == 'cancelled' and self.timer_start:
            vals['timer_start'] = False
        if vals:
            super(FsmOrder, self).write(vals)

    def _param_bool(self, key, default=True):
        param = self.env['ir.config_parameter'].sudo().search([('key', '=', key)], limit=1)
        if not param:
            return default
        return str(param.value).strip().lower() in ('1', 'true', 'yes')

    def _check_can_done(self):
        self.ensure_one()
        if self._param_bool('al_field_service.require_checklist', True):
            pending = self.checklist_line_ids.filtered(lambda l: l.is_mandatory and not l.is_done)
            if pending:
                raise UserError(_('Complete mandatory checklist items before marking the job Done: %s') % ', '.join(pending.mapped('name')))
        if self._param_bool('al_field_service.require_signature', True) and not self.signature_confirmed:
            raise UserError(_('Capture and confirm the customer signature before marking the job Done.'))

    def _get_stage(self, code):
        stage = self.env['fsm.stage'].search([('code', '=', code)], limit=1)
        if not stage:
            raise UserError(_('Stage "%s" is missing. Update Field Service stages.', code))
        return stage

    def action_plan(self):
        for order in self:
            if not order.planned_date_begin:
                order.planned_date_begin = fields.Datetime.now()
            if not order.planned_date_end:
                hours = order.allocated_hours or 2.0
                order.planned_date_end = order.planned_date_begin + timedelta(hours=hours)
            order.stage_id = order._get_stage('planned')
            order._sync_calendar_event()
            order._fsm_send_mail('mail_template_fsm_planned')
        return True

    def action_start(self):
        for order in self:
            order.timer_start = fields.Datetime.now()
            if not order.actual_date_begin:
                order.actual_date_begin = order.timer_start
            if not order.first_response_at:
                order.first_response_at = order.timer_start
            order.stage_id = order._get_stage('in_progress')
            order.message_post(body=_('Timer started at %s.', order.timer_start))
            order._fsm_send_mail('mail_template_fsm_started')
        self.mapped('technician_ids')._compute_fsm_status()
        return True

    def action_stop(self):
        for order in self:
            if not order.timer_start:
                continue
            hours = (fields.Datetime.now() - order.timer_start).total_seconds() / 3600.0
            employee = self.env['hr.employee'].search([('user_id', '=', self.env.uid)], limit=1)
            if not employee and order.technician_ids:
                employee = order.technician_ids[:1]
            if employee:
                cost = employee.sudo().hourly_cost
                line = order.project_id.fsm_service_line_ids.filtered(lambda l: l.employee_id == employee)[:1]
                if line:
                    cost = line.hourly_cost
                self.env['fsm.timesheet'].create({
                    'order_id': order.id,
                    'employee_id': employee.id,
                    'description': _('On-site work'),
                    'hours': round(hours, 2) or 0.01,
                    'hourly_cost': cost,
                })
            logged = round(hours, 2) or 0.01
            order.write({'timer_start': False})
            order.message_post(body=_('Timer stopped. Logged %s hours.', logged))
        return True

    def action_mark_response(self):
        self.write({'first_response_at': fields.Datetime.now()})
        return True

    def action_mark_done(self):
        self.action_stop()
        for order in self:
            order.stage_id = order._get_stage('done')
            if order.job_type == 'install':
                order._create_installation_record()
            order._fsm_send_mail('mail_template_fsm_done')
            if order._param_bool('al_field_service.auto_invoice_on_done', False):
                order._invoice_on_the_go()
        self.mapped('technician_ids')._compute_fsm_status()
        return True

    def action_cancel(self):
        techs = self.mapped('technician_ids')
        self.write({'stage_id': self._get_stage('cancelled').id, 'timer_start': False})
        techs._compute_fsm_status()
        return True

    def action_reset_draft(self):
        self.write({
            'stage_id': self._get_stage('draft').id,
            'actual_date_begin': False,
            'actual_date_end': False,
            'timer_start': False,
        })
        return True

    def action_confirm_signature(self):
        for order in self:
            if not order.signature:
                raise UserError(_('Draw or type a customer signature first.'))
            order.signed_on = fields.Datetime.now()
            order.signature_confirmed = True
            if not order.signed_by:
                order.signed_by = order.contact_id.name or order.partner_id.name
            order.message_post(body=_('Service report has been signed by %s.', order.signed_by))
        return True

    def action_confirm_technician_signature(self):
        for order in self:
            if not order.technician_signature:
                raise UserError(_('Technician must sign the worksheet first.'))
            order.technician_signed_on = fields.Datetime.now()
            if not order.technician_signed_by:
                order.technician_signed_by = self.env.user.name
            order.message_post(body=_('Technician %s signed the worksheet.', order.technician_signed_by))
        return True

    def action_sign_report(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Sign Report'),
            'res_model': 'fsm.sign.report',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_order_id': self.id,
                'default_signed_by': self.signed_by or self.partner_id.name,
            },
        }

    def action_print_report(self):
        return self.env.ref('al_field_service.action_report_fsm_order').report_action(self)

    def action_open_map(self):
        self.ensure_one()
        return {'type': 'ir.actions.act_url', 'url': self._navigate_url(), 'target': 'new'}

    def action_navigate(self):
        self.ensure_one()
        return {'type': 'ir.actions.act_url', 'url': self._navigate_url(), 'target': 'new'}

    def _fsm_address(self):
        self.ensure_one()
        loc = self.location_id
        parts = [loc.street, loc.city, loc.zip, loc.country_id.name] if loc else []
        addr = ', '.join(filter(None, parts))
        if addr:
            return addr
        return self.partner_id.contact_address or self.partner_id.name or ''

    def _geo(self):
        self.ensure_one()
        loc = self.location_id
        if loc and loc.partner_latitude and loc.partner_longitude:
            return loc.partner_latitude, loc.partner_longitude
        return False, False

    def _navigate_url(self):
        self.ensure_one()
        lat, lng = self._geo()
        if lat and lng:
            return f'https://www.google.com/maps/dir/?api=1&destination={lat},{lng}&travelmode=driving'
        q = quote_plus(self._fsm_address())
        return f'https://www.google.com/maps/dir/?api=1&destination={q}&travelmode=driving'

    def action_google_itinerary(self):
        orders = self.filtered(lambda o: o.state not in ('cancelled',)).sorted(
            key=lambda o: o.planned_date_begin or fields.Datetime.now()
        )
        if not orders:
            raise UserError(_('No scheduled work orders to route.'))
        url = orders._itinerary_url()
        return {'type': 'ir.actions.act_url', 'url': url, 'target': 'new'}

    def _itinerary_url(self):
        points = []
        for order in self:
            addr = order._fsm_address()
            if addr:
                points.append(quote_plus(addr))
        if not points:
            raise UserError(_('Add a customer address or service location before planning an itinerary.'))
        dest = points[-1]
        waypoints = '%7C'.join(points[:-1][:8])
        url = f'https://www.google.com/maps/dir/?api=1&origin=current+location&destination={dest}&travelmode=driving'
        if waypoints:
            url += f'&waypoints={waypoints}'
        return url

    def action_print_worksheet(self):
        return self.env.ref('al_field_service.action_report_fsm_worksheet').report_action(self)

    def action_customer_preview(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_url',
            'url': self.get_portal_url(),
            'target': 'new',
        }

    def action_view_sale(self):
        self.ensure_one()
        if not self.sale_id:
            return False
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'sale.order',
            'res_id': self.sale_id.id,
            'view_mode': 'form',
        }

    def action_view_pickings(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Deliveries'),
            'res_model': 'stock.picking',
            'view_mode': 'list,form',
            'domain': [('fsm_order_id', '=', self.id)],
        }

    def action_view_invoices(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Invoices'),
            'res_model': 'account.move',
            'view_mode': 'list,form',
            'domain': [('id', 'in', self.invoice_ids.ids)],
        }

    def action_view_attachments(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Documents'),
            'res_model': 'ir.attachment',
            'view_mode': 'kanban,list,form',
            'domain': [('res_model', '=', self._name), ('res_id', '=', self.id)],
            'context': {'default_res_model': self._name, 'default_res_id': self.id},
        }

    def action_view_children(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Sub-tasks'),
            'res_model': 'fsm.order',
            'view_mode': 'list,form',
            'domain': [('parent_id', '=', self.id)],
            'context': {'default_parent_id': self.id, 'default_partner_id': self.partner_id.id},
        }

    def _prepare_sale_order_vals(self):
        self.ensure_one()
        vals = {
            'partner_id': self.partner_id.id,
            'origin': self.name,
            'company_id': self.company_id.id,
            'client_order_ref': self.customer_po,
        }
        if self.lead_id and 'opportunity_id' in self.env['sale.order']._fields:
            vals['opportunity_id'] = self.lead_id.id
        return vals

    def _labor_product(self):
        product = self.service_product_id or self.project_id.fsm_service_product_id
        if not product:
            product_id = int(self.env['ir.config_parameter'].sudo().get_param('al_field_service.labor_product_id', '0') or 0)
            product = self.env['product.product'].browse(product_id).exists()
        if not product:
            product = self.env['product.product'].search([('type', '=', 'service')], limit=1)
        if not product:
            raise UserError(_('Configure a default labor product on the FSM project or in Settings.'))
        return product

    def _maybe_sync_sale(self):
        if self.env.context.get('fsm_skip_so_sync'):
            return
        for order in self:
            if order.so_policy != 'auto':
                continue
            if not (order.material_line_ids or order.timesheet_ids or order.service_product_id):
                continue
            order = order.with_context(fsm_skip_so_sync=True)
            if not order.sale_id:
                order.action_create_quotation()
            else:
                order._sync_sale_order()

    def _sale_line_cmds(self):
        self.ensure_one()
        cmds = []
        for mat in self.material_line_ids:
            cmds.append(Command.create({
                'product_id': mat.product_id.id,
                'name': mat.name,
                'product_uom_qty': mat.product_uom_qty,
                'product_uom_id': mat.product_uom_id.id,
                'price_unit': mat.price_unit,
                'fsm_order_id': self.id,
                'fsm_line_type': 'material',
            }))
        labor = self._labor_product()
        for ts in self.timesheet_ids:
            cmds.append(Command.create({
                'product_id': labor.id,
                'name': _('Technician labor — %s: %s', ts.employee_id.name, ts.description or ''),
                'product_uom_qty': ts.hours,
                'price_unit': ts.hourly_cost or labor.lst_price,
                'fsm_order_id': self.id,
                'fsm_line_type': 'labor',
                'fsm_employee_id': ts.employee_id.id,
            }))
        if self.service_product_id and self.service_qty and not self.timesheet_ids:
            cmds.append(Command.create({
                'product_id': self.service_product_id.id,
                'product_uom_qty': self.service_qty,
                'fsm_order_id': self.id,
                'fsm_line_type': 'labor',
            }))
        return cmds

    def action_create_quotation(self):
        self.ensure_one()
        if not self.material_line_ids and not self.timesheet_ids and not self.service_product_id:
            raise UserError(_('Add materials, timesheets or a service product before creating a quotation.'))
        if self.sale_id:
            self._sync_sale_order()
            self.message_post(body=_('Sales order %s updated from task.', self.sale_id._get_html_link()))
            return self.action_view_sale()
        so = self.env['sale.order'].create({
            **self._prepare_sale_order_vals(),
            'order_line': self._sale_line_cmds(),
        })
        self.sale_id = so
        self.message_post(body=_('Quotation %s created from task.', so._get_html_link()))
        return self.action_view_sale()

    def _sync_sale_order(self):
        self.ensure_one()
        if not self.sale_id or self.sale_id.state not in ('draft', 'sent'):
            return
        self.sale_id.order_line.filtered(lambda l: l.fsm_order_id == self).unlink()
        self.sale_id.write({'order_line': self._sale_line_cmds()})

    def action_create_invoice(self):
        self.ensure_one()
        if not self.sale_id:
            self.action_create_quotation()
        if self.sale_id.state in ('draft', 'sent'):
            self.sale_id.action_confirm()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Create Invoice'),
            'res_model': 'fsm.create.invoice',
            'view_mode': 'form',
            'target': 'new',
            'context': {'default_order_id': self.id, 'default_sale_id': self.sale_id.id},
        }

    def action_create_delivery(self):
        self.ensure_one()
        moves = []
        warehouse = (
            self.warehouse_id
            or self.env.user.fsm_warehouse_id
            or self.env.user._get_default_warehouse_id()
        )
        if not warehouse:
            raise UserError(_('Configure a warehouse on the work order or company.'))
        src = self.van_location_id or warehouse.lot_stock_id
        dest = self.partner_id.property_stock_customer
        picking_type = warehouse.out_type_id
        for line in self.material_line_ids.filtered(lambda l: l.product_id.is_storable):
            moves.append(Command.create({
                'product_id': line.product_id.id,
                'product_uom_qty': line.product_uom_qty,
                'product_uom': line.product_uom_id.id,
                'location_id': src.id,
                'location_dest_id': dest.id,
            }))
        if not moves:
            raise UserError(_('No storable products on this job to deliver.'))
        picking = self.env['stock.picking'].create({
            'picking_type_id': picking_type.id,
            'location_id': src.id,
            'location_dest_id': dest.id,
            'partner_id': self.partner_id.id,
            'origin': self.name,
            'fsm_order_id': self.id,
            'move_ids': moves,
        })
        picking.action_confirm()
        self.message_post(body=_('Delivery %s created.', picking.name))
        return self.action_view_pickings()

    def _sync_calendar_event(self):
        self.ensure_one()
        if not self.planned_date_begin:
            return
        partners = self.user_ids.partner_id
        vals = {
            'name': self.name,
            'start': self.planned_date_begin,
            'stop': self.planned_date_end or self.planned_date_begin + timedelta(hours=1),
            'partner_ids': [Command.set(partners.ids)],
            'user_id': (self.supervisor_id.user_id or self.env.user).id,
            'location': self.location_id.name or self.partner_id.name,
            'description': self.description or '',
        }
        if self.calendar_event_id:
            self.calendar_event_id.write(vals)
        else:
            self.calendar_event_id = self.env['calendar.event'].create(vals)

    def _send_rating_request(self):
        return

    @api.model
    def _cron_update_sla(self):
        open_orders = self.search([('state', 'not in', ('done', 'cancelled'))])
        open_orders._compute_sla()
        to_escalate = open_orders.filtered(lambda o: o.sla_status == 'breached' and not o.is_escalated)
        activity_type = self.env.ref('mail.mail_activity_data_todo', raise_if_not_found=False)
        for order in to_escalate:
            user = order.team_id.escalation_user_id or order.supervisor_id.user_id or order.team_id.manager_id.user_id
            if user and activity_type:
                order.activity_schedule(
                    activity_type_id=activity_type.id,
                    user_id=user.id,
                    summary=_('SLA Breached'),
                    note=_('Work order requires immediate attention.'),
                )
            order.is_escalated = True
            order.message_post(body=_('SLA Breached — escalation activity created.'))

    def _invoice_on_the_go(self):
        self.ensure_one()
        if not (self.material_line_ids or self.timesheet_ids or self.service_product_id):
            return
        if not self.sale_id:
            self.with_context(fsm_skip_so_sync=True).action_create_quotation()
        if self.sale_id.state in ('draft', 'sent'):
            self.sale_id.action_confirm()
        if self.sale_id.invoice_status == 'to invoice':
            moves = self.sale_id._create_invoices()
            moves.write({'fsm_order_id': self.id})
            self.message_post(body=_('Invoice created from task.'))

    def action_add_from_catalog(self):
        self.ensure_one()
        return super().action_add_from_catalog()

    def _get_product_catalog_domain(self):
        return super()._get_product_catalog_domain() & Domain('fsm_ok', '=', True)

    def _get_product_catalog_record_lines(self, product_ids, **kwargs):
        grouped = defaultdict(lambda: self.env['fsm.material.line'])
        for line in self.material_line_ids:
            if line.product_id.id in product_ids:
                grouped[line.product_id] |= line
        return grouped

    def _get_product_catalog_order_data(self, products, **kwargs):
        data = super()._get_product_catalog_order_data(products, **kwargs)
        for product in products:
            data[product.id]['price'] = product.lst_price
        return data

    def _is_readonly(self):
        return self.state in ('done', 'cancelled')

    def _update_order_line_info(self, product_id, quantity, **kwargs):
        line = self.material_line_ids.filtered(lambda l: l.product_id.id == product_id)[:1]
        product = self.env['product.product'].browse(product_id)
        if line:
            if quantity:
                line.product_uom_qty = quantity
            else:
                line.unlink()
        elif quantity > 0:
            self.env['fsm.material.line'].create({
                'order_id': self.id,
                'product_id': product.id,
                'name': product.display_name,
                'product_uom_qty': quantity,
                'product_uom_id': product.uom_id.id,
                'price_unit': product.lst_price,
            })
        return product.lst_price

    def get_photo_attachments(self):
        self.ensure_one()
        return self.env['ir.attachment'].search([
            ('res_model', '=', self._name),
            ('res_id', '=', self.id),
            ('mimetype', 'ilike', 'image'),
        ])

    @api.model
    def get_map_payload(self, domain=None):
        domain = list(domain or [])
        orders = self.search(domain + [('state', 'not in', ['cancelled'])], order='planned_date_begin, id')
        pins = []
        for order in orders:
            lat, lng = order._geo()
            pins.append({
                'id': order.id,
                'name': order.name,
                'partner': order.partner_id.display_name,
                'address': order._fsm_address(),
                'lat': lat or 0.0,
                'lng': lng or 0.0,
                'start': order.planned_date_begin,
                'state': order.state,
            })
        itinerary = False
        try:
            itinerary = orders._itinerary_url() if orders else False
        except UserError:
            itinerary = False
        return {'pins': pins, 'itinerary_url': itinerary}

    @api.model
    def get_gantt_payload(self, date_from=False):
        start = fields.Datetime.to_datetime(date_from) if date_from else fields.Datetime.now()
        start = start.replace(hour=0, minute=0, second=0, microsecond=0)
        end = start + timedelta(days=7)
        orders = self.search([
            ('planned_date_begin', '!=', False),
            ('planned_date_begin', '<', end),
            ('state', 'not in', ['cancelled']),
            '|', ('planned_date_end', '=', False), ('planned_date_end', '>=', start),
        ], order='planned_date_begin')
        techs = orders.mapped('technician_ids')
        if not techs:
            techs = self.env['hr.employee']
        rows = []
        for tech in techs:
            bars = []
            for order in orders.filtered(lambda o, t=tech: t in o.technician_ids):
                begin = order.planned_date_begin
                stop = order.planned_date_end or begin + timedelta(hours=order.allocated_hours or 1)
                bars.append({
                    'id': order.id,
                    'name': order.name,
                    'partner': order.partner_id.display_name,
                    'left': max(0.0, (begin - start).total_seconds() / (7 * 24 * 3600) * 100),
                    'width': max(1.5, (stop - begin).total_seconds() / (7 * 24 * 3600) * 100),
                    'state': order.state,
                })
            rows.append({'id': tech.id, 'name': tech.name, 'bars': bars})
        unassigned = orders.filtered(lambda o: not o.technician_ids)
        if unassigned:
            bars = []
            for order in unassigned:
                begin = order.planned_date_begin
                stop = order.planned_date_end or begin + timedelta(hours=order.allocated_hours or 1)
                bars.append({
                    'id': order.id,
                    'name': order.name,
                    'partner': order.partner_id.display_name,
                    'left': max(0.0, (begin - start).total_seconds() / (7 * 24 * 3600) * 100),
                    'width': max(1.5, (stop - begin).total_seconds() / (7 * 24 * 3600) * 100),
                    'state': order.state,
                })
            rows.insert(0, {'id': 0, 'name': _('Unassigned'), 'bars': bars})
        days = [(start + timedelta(days=i)).strftime('%a %d') for i in range(7)]
        return {'days': days, 'rows': rows, 'date_from': fields.Datetime.to_string(start)}

    def _fsm_send_mail(self, xmlid):
        key = {
            'mail_template_fsm_assigned': 'al_field_service.mail_assigned',
            'mail_template_fsm_planned': 'al_field_service.mail_planned',
            'mail_template_fsm_started': 'al_field_service.mail_started',
            'mail_template_fsm_done': 'al_field_service.mail_done',
            'mail_template_fsm_installation': 'al_field_service.mail_installation',
        }.get(xmlid)
        if key and not self._param_bool(key, True):
            return
        template = self.env.ref('al_field_service.%s' % xmlid, raise_if_not_found=False)
        if not template:
            return
        for order in self:
            if not (order.partner_id.email or order.technician_ids.mapped('work_email')):
                continue
            template.send_mail(order.id, force_send=False)

    def _create_installation_record(self):
        self.ensure_one()
        if self.installation_id:
            return self.installation_id
        serial = self.serial_number or (self.equipment_id.serial if self.equipment_id else False)
        if not serial:
            raise UserError(_('Enter the equipment serial number before completing an installation job.'))
        technician = self.technician_ids[:1]
        if not technician:
            raise UserError(_('Assign the installing technician before completing an installation job.'))
        install_dt = self.actual_date_end or self.actual_date_begin or fields.Datetime.now()
        start = fields.Date.to_date(install_dt)
        from dateutil.relativedelta import relativedelta
        months = self.warranty_months or 12
        installation = self.env['fsm.installation'].create({
            'partner_id': self.partner_id.id,
            'location_id': self.location_id.id,
            'order_id': self.id,
            'equipment_id': self.equipment_id.id,
            'product_id': (self.equipment_id.product_id or self.service_product_id).id,
            'serial': serial,
            'model_number': self.model_number,
            'manufacturer': self.manufacturer,
            'install_datetime': install_dt,
            'technician_id': technician.id,
            'collected_notes': self.collected_notes or self.resolution_notes,
            'warranty_start': start,
            'warranty_months': months,
            'warranty_end': start + relativedelta(months=months),
            'warranty_type': self.warranty_type or 'standard',
            'photo_ids': [
                Command.create({
                    'name': photo.name,
                    'image': photo.image,
                    'captured_on': photo.captured_on,
                    'note': photo.note,
                })
                for photo in self.photo_ids
            ],
        })
        self.installation_id = installation
        self.equipment_id = installation.equipment_id
        self.serial_number = serial
        self._fsm_send_mail('mail_template_fsm_installation')
        self.message_post(body=_('Installation record %s created. Serial %s tagged to %s.', installation.name, serial, technician.name))
        return installation


class FsmOrderPhoto(models.Model):
    _name = 'fsm.order.photo'
    _description = 'Work Order Photo'
    _order = 'id'

    order_id = fields.Many2one('fsm.order', required=True, ondelete='cascade')
    name = fields.Char(default='Photo')
    image = fields.Image(required=True)
    captured_on = fields.Datetime(default=fields.Datetime.now)
    note = fields.Char()



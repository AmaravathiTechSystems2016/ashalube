from odoo import api, fields, models
from dateutil.relativedelta import relativedelta


class FsmEquipment(models.Model):
    _name = 'fsm.equipment'
    _description = 'Installed Equipment / Asset'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'name'
    _check_company_auto = True

    name = fields.Char(required=True, tracking=True)
    code = fields.Char(copy=False, default='New', readonly=True)
    partner_id = fields.Many2one('res.partner', string='Customer', required=True, tracking=True)
    location_id = fields.Many2one('fsm.location', string='Site')
    product_id = fields.Many2one('product.product', string='Product')
    serial = fields.Char('Serial / Asset tag', tracking=True, index=True)
    model_number = fields.Char()
    manufacturer = fields.Char()
    installer_id = fields.Many2one('hr.employee', string='Installed by', tracking=True)
    installer_grade = fields.Selection(related='installer_id.fsm_grade', store=True)
    install_date = fields.Date('Installation date', tracking=True)
    warranty_start = fields.Date(tracking=True)
    warranty_months = fields.Integer(default=12)
    warranty_end = fields.Date(tracking=True)
    warranty_type = fields.Selection(
        [
            ('standard', 'Standard'),
            ('extended', 'Extended'),
            ('parts', 'Parts only'),
            ('labor', 'Labor only'),
            ('comprehensive', 'Comprehensive'),
        ],
        default='standard',
        tracking=True,
    )
    warranty_terms = fields.Text()
    warranty_reminder_sent = fields.Boolean(copy=False)
    next_service_date = fields.Date()
    active = fields.Boolean(default=True)
    company_id = fields.Many2one('res.company', default=lambda self: self.env.company)
    note = fields.Text()
    installation_ids = fields.One2many('fsm.installation', 'equipment_id')
    installation_count = fields.Integer(compute='_compute_installation_count')
    order_count = fields.Integer(compute='_compute_order_count')
    under_warranty = fields.Boolean(compute='_compute_under_warranty', store=True)

    _serial_partner_uniq = models.Constraint(
        'unique(serial, partner_id)',
        'This serial number is already tagged for this customer.',
    )

    @api.depends('warranty_end')
    def _compute_under_warranty(self):
        today = fields.Date.context_today(self)
        for eq in self:
            eq.under_warranty = bool(eq.warranty_end and eq.warranty_end >= today)

    @api.onchange('warranty_start', 'warranty_months')
    def _onchange_warranty_window(self):
        if self.warranty_start and self.warranty_months:
            self.warranty_end = self.warranty_start + relativedelta(months=self.warranty_months)

    def _compute_order_count(self):
        data = self.env['fsm.order']._read_group(
            [('equipment_id', 'in', self.ids)],
            ['equipment_id'],
            ['__count'],
        )
        mapped = {eq.id: count for eq, count in data}
        for eq in self:
            eq.order_count = mapped.get(eq.id, 0)

    def _compute_installation_count(self):
        data = self.env['fsm.installation']._read_group(
            [('equipment_id', 'in', self.ids)],
            ['equipment_id'],
            ['__count'],
        )
        mapped = {eq.id: count for eq, count in data}
        for eq in self:
            eq.installation_count = mapped.get(eq.id, 0)

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('code', 'New') == 'New':
                vals['code'] = self.env['ir.sequence'].next_by_code('fsm.equipment') or 'New'
        return super().create(vals_list)

    def action_view_orders(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Work Orders',
            'res_model': 'fsm.order',
            'view_mode': 'list,form',
            'domain': [('equipment_id', '=', self.id)],
            'context': {
                'default_equipment_id': self.id,
                'default_partner_id': self.partner_id.id,
                'default_location_id': self.location_id.id,
            },
        }

    def action_view_installations(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Installations',
            'res_model': 'fsm.installation',
            'view_mode': 'list,form',
            'domain': [('equipment_id', '=', self.id)],
            'context': {
                'default_equipment_id': self.id,
                'default_partner_id': self.partner_id.id,
                'default_serial': self.serial,
            },
        }

    @api.model
    def _cron_warranty_reminder(self):
        days = int(self.env['ir.config_parameter'].sudo().get_param('al_field_service.warranty_reminder_days', '30') or 30)
        today = fields.Date.context_today(self)
        limit = today + relativedelta(days=days)
        template = self.env.ref('al_field_service.mail_template_fsm_warranty_expiry', raise_if_not_found=False)
        records = self.search([
            ('warranty_end', '>=', today),
            ('warranty_end', '<=', limit),
            ('warranty_reminder_sent', '=', False),
            ('active', '=', True),
        ])
        for eq in records:
            if template:
                template.send_mail(eq.id, force_send=False)
            eq.warranty_reminder_sent = True
            eq.message_post(body='Warranty expiry reminder sent.')

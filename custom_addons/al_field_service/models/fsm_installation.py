from odoo import api, fields, models
from odoo.exceptions import UserError
from dateutil.relativedelta import relativedelta
from odoo.tools.translate import _


class FsmInstallation(models.Model):
    _name = 'fsm.installation'
    _description = 'Equipment Installation Record'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'install_datetime desc, id desc'
    _check_company_auto = True

    name = fields.Char(required=True, copy=False, default='New', tracking=True)
    partner_id = fields.Many2one('res.partner', string='Customer', required=True, tracking=True)
    location_id = fields.Many2one('fsm.location', string='Site')
    order_id = fields.Many2one('fsm.order', string='Work Order', index=True)
    equipment_id = fields.Many2one('fsm.equipment', string='Equipment', tracking=True)
    product_id = fields.Many2one('product.product', string='Installed product')
    serial = fields.Char('Serial Number', required=True, tracking=True, index=True)
    model_number = fields.Char()
    manufacturer = fields.Char()
    capacity = fields.Char('Capacity / Rating')
    install_datetime = fields.Datetime('Installed on', required=True, default=fields.Datetime.now, tracking=True)
    technician_id = fields.Many2one('hr.employee', string='Installing technician', required=True, tracking=True)
    technician_grade = fields.Selection(related='technician_id.fsm_grade', store=True)
    collected_notes = fields.Html('Collected information')
    commissioning_notes = fields.Text()
    photo_ids = fields.One2many('fsm.installation.photo', 'installation_id', string='Installation photos')
    photo_count = fields.Integer(compute='_compute_photo_count')
    company_id = fields.Many2one('res.company', default=lambda self: self.env.company, required=True)
    warranty_start = fields.Date()
    warranty_end = fields.Date()
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
    warranty_terms = fields.Text()
    state = fields.Selection(
        [('draft', 'Draft'), ('done', 'Completed')],
        default='done',
        tracking=True,
    )

    @api.depends('photo_ids')
    def _compute_photo_count(self):
        for rec in self:
            rec.photo_count = len(rec.photo_ids)

    @api.onchange('warranty_start', 'warranty_months')
    def _onchange_warranty_window(self):
        if self.warranty_start and self.warranty_months:
            self.warranty_end = self.warranty_start + relativedelta(months=self.warranty_months)

    @api.onchange('serial', 'equipment_id')
    def _onchange_serial(self):
        if self.equipment_id and not self.serial:
            self.serial = self.equipment_id.serial

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', 'New') == 'New':
                vals['name'] = self.env['ir.sequence'].next_by_code('fsm.installation') or 'New'
        records = super().create(vals_list)
        records._sync_equipment()
        return records

    def write(self, vals):
        res = super().write(vals)
        if any(k in vals for k in ('serial', 'technician_id', 'install_datetime', 'warranty_start', 'warranty_end', 'warranty_months', 'warranty_type', 'product_id', 'partner_id', 'location_id')):
            self._sync_equipment()
        return res

    def _sync_equipment(self):
        Equipment = self.env['fsm.equipment']
        for rec in self:
            eq = rec.equipment_id
            vals = {
                'name': rec.equipment_id.name or rec.product_id.display_name or rec.serial,
                'partner_id': rec.partner_id.id,
                'location_id': rec.location_id.id,
                'product_id': rec.product_id.id,
                'serial': rec.serial,
                'installer_id': rec.technician_id.id,
                'install_date': rec.install_datetime.date() if rec.install_datetime else False,
                'warranty_start': rec.warranty_start,
                'warranty_end': rec.warranty_end,
                'warranty_months': rec.warranty_months,
                'warranty_type': rec.warranty_type,
                'warranty_terms': rec.warranty_terms,
                'model_number': rec.model_number,
                'manufacturer': rec.manufacturer,
            }
            if eq:
                eq.write({k: v for k, v in vals.items() if v or k in ('serial', 'installer_id')})
            else:
                existing = Equipment.search([('serial', '=', rec.serial), ('partner_id', '=', rec.partner_id.id)], limit=1)
                rec.equipment_id = existing or Equipment.create(vals)

    def action_open_order(self):
        self.ensure_one()
        if not self.order_id:
            raise UserError(_('No work order linked.'))
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'fsm.order',
            'res_id': self.order_id.id,
            'view_mode': 'form',
        }


class FsmInstallationPhoto(models.Model):
    _name = 'fsm.installation.photo'
    _description = 'Installation Photo'
    _order = 'sequence, id'

    installation_id = fields.Many2one('fsm.installation', required=True, ondelete='cascade')
    name = fields.Char(default='Photo')
    sequence = fields.Integer(default=10)
    image = fields.Image(required=True)
    captured_on = fields.Datetime(default=fields.Datetime.now)
    note = fields.Char()

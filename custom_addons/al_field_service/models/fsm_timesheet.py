from odoo import api, fields, models


class FsmTimesheet(models.Model):
    _name = 'fsm.timesheet'
    _description = 'Field Service Timesheet'
    _order = 'date, id'

    order_id = fields.Many2one('fsm.order', required=True, ondelete='cascade', index=True)
    date = fields.Date(required=True, default=fields.Date.context_today)
    employee_id = fields.Many2one('hr.employee', required=True)
    description = fields.Char()
    hours = fields.Float(required=True, default=1.0)
    hourly_cost = fields.Monetary(currency_field='currency_id')
    total_cost = fields.Monetary(compute='_compute_total_cost', store=True, currency_field='currency_id')
    currency_id = fields.Many2one(related='order_id.currency_id', store=True)
    company_id = fields.Many2one(related='order_id.company_id', store=True)
    sale_line_id = fields.Many2one('sale.order.line', copy=False)

    @api.model_create_multi
    def create(self, vals_list):
        Employee = self.env['hr.employee'].sudo()
        for vals in vals_list:
            if not vals.get('hourly_cost') and vals.get('employee_id'):
                vals['hourly_cost'] = Employee.browse(vals['employee_id']).hourly_cost
        records = super().create(vals_list)
        records.mapped('order_id')._maybe_sync_sale()
        return records

    def write(self, vals):
        res = super().write(vals)
        if any(k in vals for k in ('hours', 'hourly_cost', 'employee_id', 'description')):
            self.mapped('order_id')._maybe_sync_sale()
        return res

    @api.onchange('employee_id')
    def _onchange_employee_id(self):
        if self.employee_id:
            self.hourly_cost = self.employee_id.sudo().hourly_cost
            line = self.order_id.project_id.fsm_service_line_ids.filtered(
                lambda l: l.employee_id == self.employee_id
            )[:1]
            if line:
                self.hourly_cost = line.hourly_cost

    @api.depends('hours', 'hourly_cost')
    def _compute_total_cost(self):
        for line in self:
            line.total_cost = line.hours * line.hourly_cost

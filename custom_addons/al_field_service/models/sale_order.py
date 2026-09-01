from odoo import fields, models
from odoo.exceptions import UserError
from odoo.tools.translate import _


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    fsm_order_ids = fields.One2many('fsm.order', 'sale_id')
    fsm_order_count = fields.Integer(compute='_compute_fsm_order_count')

    def _compute_fsm_order_count(self):
        data = self.env['fsm.order']._read_group(
            [('sale_id', 'in', self.ids)], ['sale_id'], ['__count']
        )
        mapped = {order.id: count for order, count in data}
        for so in self:
            so.fsm_order_count = mapped.get(so.id, 0)

    def _action_confirm(self):
        res = super()._action_confirm()
        self._create_fsm_orders_from_lines()
        return res

    def _create_fsm_orders_from_lines(self):
        FsmOrder = self.env['fsm.order']
        project_id = int(self.env['ir.config_parameter'].sudo().get_param('al_field_service.default_project_id', '0') or 0)
        for so in self:
            for line in so.order_line.filtered(lambda l: l.product_id.fsm_create_task and not l.fsm_order_id):
                order = FsmOrder.create({
                    'name': '%s — %s' % (so.name, line.product_id.display_name),
                    'partner_id': so.partner_id.id,
                    'sale_id': so.id,
                    'sale_line_id': line.id,
                    'source': 'sale',
                    'project_id': project_id or False,
                    'service_product_id': line.product_id.id,
                    'service_qty': line.product_uom_qty,
                    'allocated_hours': line.product_uom_qty if line.product_id.type == 'service' else 0.0,
                    'customer_po': so.client_order_ref,
                    'company_id': so.company_id.id,
                    'description': line.name,
                })
                line.fsm_order_id = order.id

    def action_create_fsm_order(self):
        self.ensure_one()
        if not self.partner_id:
            raise UserError(_('Set a customer first.'))
        existing = self.fsm_order_ids[:1]
        if existing:
            return self.action_view_fsm_orders()
        project_id = int(self.env['ir.config_parameter'].sudo().get_param('al_field_service.default_project_id', '0') or 0)
        line = self.order_line[:1]
        order = self.env['fsm.order'].create({
            'name': self.name,
            'partner_id': self.partner_id.id,
            'sale_id': self.id,
            'sale_line_id': line.id,
            'source': 'sale',
            'project_id': project_id or False,
            'service_product_id': line.product_id.id if line and line.product_id.type == 'service' else False,
            'service_qty': line.product_uom_qty if line else 1.0,
            'customer_po': self.client_order_ref,
            'company_id': self.company_id.id,
        })
        if line:
            line.fsm_order_id = order.id
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'fsm.order',
            'res_id': order.id,
            'view_mode': 'form',
        }

    def action_view_fsm_orders(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Work Orders'),
            'res_model': 'fsm.order',
            'view_mode': 'list,form',
            'domain': [('sale_id', '=', self.id)],
            'context': {'default_sale_id': self.id, 'default_partner_id': self.partner_id.id, 'default_source': 'sale'},
        }


class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    fsm_order_id = fields.Many2one('fsm.order', index=True, copy=False)
    fsm_line_type = fields.Selection([('material', 'Material'), ('labor', 'Labor')])
    fsm_employee_id = fields.Many2one('hr.employee', string='Technician')

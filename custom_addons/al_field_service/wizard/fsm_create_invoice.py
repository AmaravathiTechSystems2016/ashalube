from odoo import fields, models
from odoo.exceptions import UserError
from odoo.tools.translate import _


class FsmCreateInvoice(models.TransientModel):
    _name = 'fsm.create.invoice'
    _description = 'Create Invoice from Field Service'

    order_id = fields.Many2one('fsm.order', required=True)
    sale_id = fields.Many2one('sale.order', required=True)
    advance_payment_method = fields.Selection(
        [
            ('delivered', 'Regular invoice'),
            ('percentage', 'Down payment (percentage)'),
            ('fixed', 'Down payment (fixed amount)'),
        ],
        default='delivered',
        required=True,
        string='Create Invoice',
    )
    amount = fields.Float('Down Payment %')
    fixed_amount = fields.Monetary('Down Payment Amount')
    currency_id = fields.Many2one(related='sale_id.currency_id')
    deduct_down_payments = fields.Boolean(default=True)

    def action_create_invoices(self):
        self.ensure_one()
        sale = self.sale_id
        if sale.state not in ('sale', 'done'):
            sale.action_confirm()
        wizard = self.env['sale.advance.payment.inv'].with_context(active_ids=sale.ids, active_id=sale.id).create({
            'sale_order_ids': [(6, 0, sale.ids)],
            'advance_payment_method': self.advance_payment_method,
            'amount': self.amount,
            'fixed_amount': self.fixed_amount,
            'deduct_down_payments': self.deduct_down_payments,
        })
        action = wizard.create_invoices()
        invoices = sale.invoice_ids
        invoices.write({'fsm_order_id': self.order_id.id})
        self.order_id.message_post(body=_('Invoice created from task.'))
        return action or {
            'type': 'ir.actions.act_window',
            'res_model': 'account.move',
            'view_mode': 'list,form',
            'domain': [('id', 'in', invoices.ids)],
        }

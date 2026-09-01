from odoo import fields, models


class AccountMove(models.Model):
    _inherit = 'account.move'

    fsm_order_id = fields.Many2one('fsm.order', index=True, copy=False)

    def _get_fsm_material_lines(self):
        self.ensure_one()
        return self.invoice_line_ids.filtered(lambda l: l.fsm_line_type == 'material' and l.display_type == 'product')

    def _get_fsm_labor_lines(self):
        self.ensure_one()
        return self.invoice_line_ids.filtered(lambda l: l.fsm_line_type == 'labor' and l.display_type == 'product')


class AccountMoveLine(models.Model):
    _inherit = 'account.move.line'

    fsm_order_id = fields.Many2one('fsm.order', related='sale_line_ids.fsm_order_id', store=True)
    fsm_line_type = fields.Selection(related='sale_line_ids.fsm_line_type', store=True)
    fsm_employee_id = fields.Many2one('hr.employee', related='sale_line_ids.fsm_employee_id', store=True)

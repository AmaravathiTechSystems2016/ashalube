from odoo import fields, models


class StockPicking(models.Model):
    _inherit = 'stock.picking'

    fsm_order_id = fields.Many2one('fsm.order', index=True, copy=False)

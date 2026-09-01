from odoo import fields, models


class ResUsers(models.Model):
    _inherit = 'res.users'

    fsm_warehouse_id = fields.Many2one(
        'stock.warehouse',
        string='Field Service Warehouse',
        help='Default warehouse for parts used on work orders (van restock / main store).',
    )

    @property
    def SELF_READABLE_FIELDS(self):
        return super().SELF_READABLE_FIELDS + ['fsm_warehouse_id']

    @property
    def SELF_WRITEABLE_FIELDS(self):
        return super().SELF_WRITEABLE_FIELDS + ['fsm_warehouse_id']

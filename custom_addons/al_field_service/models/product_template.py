from odoo import fields, models


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    fsm_ok = fields.Boolean(
        'Used in Field Service',
        default=False,
        help='Show this product in the on-site Field Service catalog.',
    )
    fsm_create_task = fields.Boolean(
        'Create Field Service Task',
        help='When a sales order with this service is confirmed, create a work order automatically.',
    )

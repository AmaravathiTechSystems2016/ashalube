from odoo import api, fields, models


class FsmMaterialLine(models.Model):
    _name = 'fsm.material.line'
    _description = 'Field Service Material'
    _order = 'id'

    order_id = fields.Many2one('fsm.order', required=True, ondelete='cascade', index=True)
    product_id = fields.Many2one('product.product', required=True)
    name = fields.Char('Description', required=True)
    product_uom_qty = fields.Float('Quantity', default=1.0, required=True)
    product_uom_id = fields.Many2one('uom.uom', string='UoM', required=True)
    price_unit = fields.Monetary(currency_field='currency_id')
    price_subtotal = fields.Monetary(compute='_compute_subtotal', store=True, currency_field='currency_id')
    currency_id = fields.Many2one(related='order_id.currency_id', store=True)
    company_id = fields.Many2one(related='order_id.company_id', store=True)
    sale_line_id = fields.Many2one('sale.order.line', copy=False)

    @api.onchange('product_id')
    def _onchange_product_id(self):
        if self.product_id:
            self.name = self.product_id.display_name
            self.product_uom_id = self.product_id.uom_id
            self.price_unit = self.product_id.lst_price

    @api.depends('product_uom_qty', 'price_unit')
    def _compute_subtotal(self):
        for line in self:
            line.price_subtotal = line.product_uom_qty * line.price_unit

    def _get_product_catalog_lines_data(self, **kwargs):
        if len(self) == 1:
            return {
                'quantity': self.product_uom_qty,
                'price': self.price_unit,
                'readOnly': self.order_id._is_readonly(),
                'uomDisplayName': self.product_uom_id.display_name,
            }
        return {
            'quantity': 0,
            'price': 0,
            'readOnly': True,
            'uomDisplayName': '',
        }

    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)
        records.mapped('order_id')._maybe_sync_sale()
        return records

    def write(self, vals):
        res = super().write(vals)
        if any(k in vals for k in ('product_id', 'product_uom_qty', 'price_unit', 'name')):
            self.mapped('order_id')._maybe_sync_sale()
        return res

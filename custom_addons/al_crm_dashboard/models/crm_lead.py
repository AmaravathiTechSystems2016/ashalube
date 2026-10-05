from odoo import api, fields, models


class CrmLead(models.Model):
    _inherit = 'crm.lead'

    al_enquiry_date = fields.Date(
        string='Enquiry Date',
        default=fields.Date.context_today,
        tracking=True,
        copy=True,
    )
    al_quantity = fields.Float(
        string='Quantity',
        digits='Product Unit of Measure',
        default=0.0,
        tracking=True,
    )
    al_rate = fields.Monetary(
        string='Rate',
        currency_field='company_currency',
        default=0.0,
        tracking=True,
        help='Cost per item.',
    )
    al_value = fields.Monetary(
        string='Value',
        currency_field='company_currency',
        default=0.0,
        tracking=True,
        help='Quantity multiplied by rate. An imported value is kept when quantity and rate are not set.',
    )

    @api.onchange('al_quantity', 'al_rate', 'company_id')
    def _onchange_al_quantity_rate(self):
        currency = self.company_currency or self.env.company.currency_id
        self.al_value = currency.round((self.al_quantity or 0.0) * (self.al_rate or 0.0))

    def _apply_item_value(self, vals, quantity=0.0, rate=0.0):
        """Fill Value from Quantity x Rate unless the row already has a Value.

        Import can map Quantity, Rate, Value, or any combination. A provided
        Value is stored as-is. Quantity and Rate fill Value when Value is empty.
        """
        if vals.get('al_value'):
            return
        if 'al_quantity' not in vals and 'al_rate' not in vals:
            return
        if 'al_quantity' in vals:
            quantity = vals.get('al_quantity') or 0.0
        if 'al_rate' in vals:
            rate = vals.get('al_rate') or 0.0
        company = self.env.company
        if vals.get('company_id'):
            company = self.env['res.company'].browse(vals['company_id'])
        elif len(self) == 1 and self.company_id:
            company = self.company_id
        currency = company.currency_id or self.env.company.currency_id
        vals['al_value'] = currency.round((quantity or 0.0) * (rate or 0.0))

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            self._apply_item_value(vals)
        return super().create(vals_list)

    def write(self, vals):
        if ('al_quantity' in vals or 'al_rate' in vals) and not vals.get('al_value'):
            if len(self) <= 1 or ('al_quantity' in vals and 'al_rate' in vals):
                vals = dict(vals)
                self._apply_item_value(
                    vals,
                    quantity=self[:1].al_quantity,
                    rate=self[:1].al_rate,
                )
                return super().write(vals)
            for lead in self:
                lead_vals = dict(vals)
                lead._apply_item_value(lead_vals, quantity=lead.al_quantity, rate=lead.al_rate)
                super(CrmLead, lead).write(lead_vals)
            return True
        return super().write(vals)

    def _merge_get_fields(self):
        return super()._merge_get_fields() + ['al_enquiry_date', 'al_quantity', 'al_rate', 'al_value']

from odoo import api, fields, models


class FsmLocation(models.Model):
    _name = 'fsm.location'
    _description = 'Service Location'
    _inherit = ['mail.thread']
    _order = 'name'
    _check_company_auto = True

    name = fields.Char(required=True, tracking=True)
    partner_id = fields.Many2one('res.partner', string='Customer', required=True, tracking=True)
    contact_name = fields.Char('Onsite Contact')
    phone = fields.Char()
    email = fields.Char()
    active = fields.Boolean(default=True)
    company_id = fields.Many2one('res.company', default=lambda self: self.env.company)

    street = fields.Char()
    street2 = fields.Char()
    city = fields.Char()
    state_id = fields.Many2one('res.country.state')
    zip = fields.Char()
    country_id = fields.Many2one('res.country')
    partner_latitude = fields.Float(digits=(10, 7), string='Latitude')
    partner_longitude = fields.Float(digits=(10, 7), string='Longitude')
    access_notes = fields.Text(
        'Location instructions',
        help='Gate pass, parking, safety, site access.',
    )
    map_url = fields.Char(compute='_compute_map_url')
    order_count = fields.Integer(compute='_compute_order_count')

    @api.onchange('partner_id')
    def _onchange_partner_id(self):
        if self.partner_id:
            p = self.partner_id
            self.street = p.street
            self.street2 = p.street2
            self.city = p.city
            self.state_id = p.state_id
            self.zip = p.zip
            self.country_id = p.country_id
            self.phone = self.phone or p.phone
            self.email = self.email or p.email
            if not self.name:
                self.name = p.name

    def _compute_map_url(self):
        for loc in self:
            q = ', '.join(filter(None, [
                loc.street, loc.city, loc.zip,
                loc.country_id.name if loc.country_id else '',
            ]))
            if loc.partner_latitude and loc.partner_longitude:
                loc.map_url = (
                    f'https://www.google.com/maps?q={loc.partner_latitude},{loc.partner_longitude}'
                )
            elif q:
                loc.map_url = f'https://www.google.com/maps/search/?api=1&query={q}'
            else:
                loc.map_url = False

    def _compute_order_count(self):
        data = self.env['fsm.order']._read_group(
            [('location_id', 'in', self.ids)],
            ['location_id'],
            ['__count'],
        )
        mapped = {loc.id: count for loc, count in data}
        for loc in self:
            loc.order_count = mapped.get(loc.id, 0)

    def action_view_orders(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Work Orders',
            'res_model': 'fsm.order',
            'view_mode': 'list,kanban,form',
            'domain': [('location_id', '=', self.id)],
            'context': {'default_location_id': self.id, 'default_partner_id': self.partner_id.id},
        }

    def action_open_map(self):
        self.ensure_one()
        return {'type': 'ir.actions.act_url', 'url': self.map_url or 'https://maps.google.com', 'target': 'new'}

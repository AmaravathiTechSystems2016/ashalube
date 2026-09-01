from odoo import fields, models
from odoo.tools.translate import _


class ResPartner(models.Model):
    _inherit = 'res.partner'

    fsm_order_ids = fields.One2many('fsm.order', 'partner_id')
    fsm_order_count = fields.Integer(compute='_compute_fsm_counts')
    fsm_location_count = fields.Integer(compute='_compute_fsm_counts')
    fsm_equipment_count = fields.Integer(compute='_compute_fsm_counts')

    def _compute_fsm_counts(self):
        orders = self.env['fsm.order']._read_group(
            [('partner_id', 'child_of', self.ids)], ['partner_id'], ['__count']
        )
        locs = self.env['fsm.location']._read_group(
            [('partner_id', 'child_of', self.ids)], ['partner_id'], ['__count']
        )
        eqs = self.env['fsm.equipment']._read_group(
            [('partner_id', 'child_of', self.ids)], ['partner_id'], ['__count']
        )
        om = {p.id: c for p, c in orders}
        lm = {p.id: c for p, c in locs}
        em = {p.id: c for p, c in eqs}
        for partner in self:
            partner.fsm_order_count = om.get(partner.id, 0)
            partner.fsm_location_count = lm.get(partner.id, 0)
            partner.fsm_equipment_count = em.get(partner.id, 0)

    def action_view_fsm_orders(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Work Orders'),
            'res_model': 'fsm.order',
            'view_mode': 'list,kanban,form',
            'domain': [('partner_id', 'child_of', self.id)],
            'context': {'default_partner_id': self.id},
        }

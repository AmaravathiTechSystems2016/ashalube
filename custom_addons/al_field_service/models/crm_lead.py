from odoo import fields, models
from odoo.exceptions import UserError
from odoo.tools.translate import _


class CrmLead(models.Model):
    _inherit = 'crm.lead'

    fsm_order_ids = fields.One2many('fsm.order', 'lead_id')
    fsm_order_count = fields.Integer(compute='_compute_fsm_order_count')

    def _compute_fsm_order_count(self):
        data = self.env['fsm.order']._read_group(
            [('lead_id', 'in', self.ids)], ['lead_id'], ['__count']
        )
        mapped = {lead.id: count for lead, count in data}
        for lead in self:
            lead.fsm_order_count = mapped.get(lead.id, 0)

    def action_create_fsm_order(self):
        self.ensure_one()
        if not self.partner_id:
            raise UserError(_('Set a customer on the opportunity first.'))
        project_id = int(self.env['ir.config_parameter'].sudo().get_param('al_field_service.default_project_id', '0') or 0)
        order = self.env['fsm.order'].create({
            'name': self.name,
            'partner_id': self.partner_id.id,
            'phone': self.phone,
            'email': self.email_from,
            'description': self.description,
            'lead_id': self.id,
            'source': 'crm',
            'project_id': project_id or False,
            'company_id': self.company_id.id or self.env.company.id,
        })
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
            'domain': [('lead_id', '=', self.id)],
            'context': {'default_lead_id': self.id, 'default_partner_id': self.partner_id.id, 'default_source': 'crm'},
        }

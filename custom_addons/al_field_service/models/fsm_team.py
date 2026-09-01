from odoo import api, fields, models


class FsmTeam(models.Model):
    _name = 'fsm.team'
    _description = 'Service Team'
    _inherit = ['mail.thread']
    _order = 'name'
    _check_company_auto = True

    name = fields.Char(required=True, tracking=True)
    manager_id = fields.Many2one('hr.employee', string='Team Manager', tracking=True)
    member_ids = fields.Many2many('hr.employee', string='Members')
    skill_ids = fields.Many2many('fsm.skill', string='Skills covered')
    active = fields.Boolean(default=True)
    company_id = fields.Many2one('res.company', default=lambda self: self.env.company, required=True)
    color = fields.Integer()
    note = fields.Html()

    invoicing_policy = fields.Selection(
        [
            ('manual', 'Manual'),
            ('auto', 'Automatic sales order'),
        ],
        default='manual',
        required=True,
        tracking=True,
    )
    escalation_user_id = fields.Many2one('res.users', string='Escalation Responsible')
    first_response_sla = fields.Float('First Response SLA (Hours)', default=2.0)
    resolution_sla = fields.Float('Resolution SLA (Hours)', default=24.0)
    at_risk_ratio = fields.Float(
        'At-risk threshold',
        default=0.25,
        help='Mark At Risk when remaining SLA time is below this ratio of the window (0.25 = last 25%).',
    )

    order_count = fields.Integer(compute='_compute_order_count')

    def _compute_order_count(self):
        data = self.env['fsm.order']._read_group(
            [('team_id', 'in', self.ids)],
            ['team_id'],
            ['__count'],
        )
        mapped = {team.id: count for team, count in data}
        for team in self:
            team.order_count = mapped.get(team.id, 0)

    def action_view_orders(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Work Orders',
            'res_model': 'fsm.order',
            'view_mode': 'list,kanban,form',
            'domain': [('team_id', '=', self.id)],
            'context': {'default_team_id': self.id},
        }

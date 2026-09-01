from odoo import fields, models


class ProjectProject(models.Model):
    _inherit = 'project.project'

    is_fsm = fields.Boolean('Field Service Project', default=False, index=True)
    fsm_worksheet_template_id = fields.Many2one('fsm.worksheet.template')
    fsm_service_product_id = fields.Many2one('product.product', domain=[('type', '=', 'service')])
    fsm_service_line_ids = fields.One2many('fsm.project.service.line', 'project_id', string='Service lines')
    fsm_order_count = fields.Integer(compute='_compute_fsm_order_count')
    allocated_hours = fields.Float()
    fsm_date_from = fields.Date('Planned Date (From)')
    fsm_date_to = fields.Date('Planned Date (To)')

    def _compute_fsm_order_count(self):
        data = self.env['fsm.order']._read_group(
            [('project_id', 'in', self.ids)], ['project_id'], ['__count']
        )
        mapped = {project.id: count for project, count in data}
        for project in self:
            project.fsm_order_count = mapped.get(project.id, 0)

    def action_view_fsm_orders(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Work Orders',
            'res_model': 'fsm.order',
            'view_mode': 'list,kanban,form',
            'domain': [('project_id', '=', self.id)],
            'context': {
                'default_project_id': self.id,
                'default_partner_id': self.partner_id.id,
            },
        }


class FsmProjectServiceLine(models.Model):
    _name = 'fsm.project.service.line'
    _description = 'FSM Project employee rate'

    project_id = fields.Many2one('project.project', required=True, ondelete='cascade')
    employee_id = fields.Many2one('hr.employee', required=True)
    hourly_cost = fields.Float(required=True)
    currency_id = fields.Many2one(related='project_id.currency_id')

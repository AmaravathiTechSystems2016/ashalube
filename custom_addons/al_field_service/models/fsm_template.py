from odoo import fields, models


class FsmOrderTemplate(models.Model):
    _name = 'fsm.order.template'
    _description = 'Field Service Job Template'
    _order = 'name'

    name = fields.Char(required=True, translate=True)
    active = fields.Boolean(default=True)
    job_type = fields.Selection(
        [
            ('install', 'Installation'),
            ('repair', 'Repair'),
            ('inspection', 'Inspection'),
            ('preventive', 'Preventive'),
            ('emergency', 'Emergency'),
            ('survey', 'Survey'),
            ('other', 'Other'),
        ],
        default='repair',
        required=True,
    )
    priority = fields.Selection([('0', 'Normal'), ('1', 'Low'), ('2', 'High')], default='0')
    team_id = fields.Many2one('fsm.team')
    project_id = fields.Many2one('project.project', domain=[('is_fsm', '=', True)])
    checklist_template_id = fields.Many2one('fsm.checklist.template')
    worksheet_template_id = fields.Many2one('fsm.worksheet.template')
    skill_ids = fields.Many2many('fsm.skill')
    tag_ids = fields.Many2many('fsm.tag')
    allocated_hours = fields.Float(default=2.0)
    service_product_id = fields.Many2one('product.product', domain=[('type', '=', 'service')])
    description = fields.Html()
    company_id = fields.Many2one('res.company', default=lambda self: self.env.company)

    def _prepare_order_vals(self):
        self.ensure_one()
        return {
            'job_type': self.job_type,
            'priority': self.priority,
            'team_id': self.team_id.id,
            'project_id': self.project_id.id,
            'checklist_template_id': self.checklist_template_id.id,
            'worksheet_template_id': self.worksheet_template_id.id,
            'skill_ids': [(6, 0, self.skill_ids.ids)],
            'tag_ids': [(6, 0, self.tag_ids.ids)],
            'allocated_hours': self.allocated_hours,
            'service_product_id': self.service_product_id.id,
            'description': self.description,
            'is_emergency': self.job_type == 'emergency',
            'is_preventive': self.job_type == 'preventive',
        }

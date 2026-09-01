from odoo import api, fields, models


class FsmChecklistTemplate(models.Model):
    _name = 'fsm.checklist.template'
    _description = 'Checklist Template'
    _order = 'name'

    name = fields.Char(required=True, translate=True)
    active = fields.Boolean(default=True)
    company_id = fields.Many2one('res.company', default=lambda self: self.env.company)
    line_ids = fields.One2many('fsm.checklist.template.line', 'template_id', string='Items', copy=True)


class FsmChecklistTemplateLine(models.Model):
    _name = 'fsm.checklist.template.line'
    _description = 'Checklist Template Item'
    _order = 'sequence, id'

    template_id = fields.Many2one('fsm.checklist.template', required=True, ondelete='cascade')
    sequence = fields.Integer(default=10)
    name = fields.Char(required=True, translate=True)
    is_mandatory = fields.Boolean(default=True)


class FsmChecklistLine(models.Model):
    _name = 'fsm.checklist.line'
    _description = 'Work Order Checklist Item'
    _order = 'sequence, id'

    order_id = fields.Many2one('fsm.order', required=True, ondelete='cascade', index=True)
    sequence = fields.Integer(default=10)
    name = fields.Char(required=True)
    is_mandatory = fields.Boolean()
    is_done = fields.Boolean()
    note = fields.Char()
    done_by_id = fields.Many2one('hr.employee')
    done_date = fields.Datetime()

    def write(self, vals):
        if vals.get('is_done') and 'done_date' not in vals:
            vals['done_date'] = fields.Datetime.now()
            if 'done_by_id' not in vals:
                employee = self.env['hr.employee'].search([('user_id', '=', self.env.uid)], limit=1)
                if employee:
                    vals['done_by_id'] = employee.id
        return super().write(vals)

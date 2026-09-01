from odoo import fields, models


class FsmStage(models.Model):
    _name = 'fsm.stage'
    _description = 'Field Service Stage'
    _order = 'sequence, id'
    _check_company_auto = True

    name = fields.Char(required=True, translate=True)
    code = fields.Selection(
        [
            ('draft', 'Draft'),
            ('planned', 'Planned'),
            ('in_progress', 'In Progress'),
            ('done', 'Done'),
            ('cancelled', 'Cancelled'),
        ],
        required=True,
        default='draft',
    )
    sequence = fields.Integer(default=10)
    fold = fields.Boolean('Folded in Kanban')
    is_closed = fields.Boolean('Closed stage')
    active = fields.Boolean(default=True)
    company_id = fields.Many2one('res.company', default=lambda self: self.env.company)

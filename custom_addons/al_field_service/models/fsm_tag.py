from odoo import fields, models


class FsmTag(models.Model):
    _name = 'fsm.tag'
    _description = 'Field Service Tag'
    _order = 'name'

    name = fields.Char(required=True, translate=True)
    color = fields.Integer(default=0)
    active = fields.Boolean(default=True)
    company_id = fields.Many2one('res.company', default=lambda self: self.env.company)

    _name_uniq = models.Constraint(
        'unique(name, company_id)',
        'Tag name must be unique per company.',
    )


class FsmSkill(models.Model):
    _name = 'fsm.skill'
    _description = 'Technician Skill'
    _order = 'name'

    name = fields.Char(required=True, translate=True)
    color = fields.Integer()
    active = fields.Boolean(default=True)

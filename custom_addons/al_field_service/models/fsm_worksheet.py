from odoo import fields, models


class FsmWorksheetTemplate(models.Model):
    _name = 'fsm.worksheet.template'
    _description = 'Worksheet Template'
    _order = 'name'

    name = fields.Char(required=True, translate=True)
    color = fields.Integer()
    active = fields.Boolean(default=True)
    company_ids = fields.Many2many('res.company', string='Companies')
    body = fields.Html('Service worksheet', translate=True, sanitize=False)
    worksheet_count = fields.Integer(compute='_compute_worksheet_count')

    def _compute_worksheet_count(self):
        data = self.env['fsm.order']._read_group(
            [('worksheet_template_id', 'in', self.ids)],
            ['worksheet_template_id'],
            ['__count'],
        )
        mapped = {tpl.id: count for tpl, count in data}
        for tpl in self:
            tpl.worksheet_count = mapped.get(tpl.id, 0)

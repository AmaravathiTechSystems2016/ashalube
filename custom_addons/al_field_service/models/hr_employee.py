from odoo import api, fields, models


class HrEmployee(models.Model):
    _inherit = 'hr.employee'

    fsm_skill_ids = fields.Many2many('fsm.skill', string='Field Service Skills')
    fsm_van_location_id = fields.Many2one('stock.location', string='Van Stock Location')
    fsm_grade = fields.Selection(
        [('a', 'A'), ('b', 'B'), ('c', 'C'), ('d', 'D')],
        string='Technician grade',
        help='A = senior / specialist, B = independent, C = junior, D = trainee.',
    )
    fsm_status_override = fields.Selection(
        [('auto', 'Automatic'), ('idle', 'Idle'), ('busy', 'Busy'), ('off', 'Off duty')],
        default='auto',
        required=True,
        string='Status mode',
    )
    fsm_status = fields.Selection(
        [('idle', 'Idle'), ('busy', 'Busy'), ('off', 'Off duty')],
        compute='_compute_fsm_status',
        store=True,
        string='Field status',
    )
    fsm_open_job_count = fields.Integer(compute='_compute_fsm_status', store=True)
    fsm_serial_count = fields.Integer(compute='_compute_fsm_serial_count')

    @api.depends('fsm_status_override')
    def _compute_fsm_status(self):
        mapped = dict.fromkeys(self.ids, 0)
        if self.ids:
            data = self.env['fsm.order']._read_group(
                [('technician_ids', 'in', self.ids), ('state', '=', 'in_progress')],
                ['technician_ids'],
                ['__count'],
            )
            for tech, count in data:
                mapped[tech.id] = mapped.get(tech.id, 0) + count
        for emp in self:
            open_jobs = mapped.get(emp.id, 0)
            emp.fsm_open_job_count = open_jobs
            if emp.fsm_status_override == 'off':
                emp.fsm_status = 'off'
            elif emp.fsm_status_override in ('idle', 'busy'):
                emp.fsm_status = emp.fsm_status_override
            else:
                emp.fsm_status = 'busy' if open_jobs else 'idle'

    def _compute_fsm_serial_count(self):
        data = self.env['fsm.equipment']._read_group(
            [('installer_id', 'in', self.ids)],
            ['installer_id'],
            ['__count'],
        )
        mapped = {emp.id: count for emp, count in data}
        for emp in self:
            emp.fsm_serial_count = mapped.get(emp.id, 0)

    def action_view_installed_serials(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Installed serials',
            'res_model': 'fsm.equipment',
            'view_mode': 'list,form',
            'domain': [('installer_id', '=', self.id)],
            'context': {'default_installer_id': self.id},
        }

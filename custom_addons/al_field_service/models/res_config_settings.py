from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    fsm_default_project_id = fields.Many2one(
        'project.project',
        domain=[('is_fsm', '=', True)],
        config_parameter='al_field_service.default_project_id',
    )
    fsm_labor_product_id = fields.Many2one(
        'product.product',
        domain=[('type', '=', 'service')],
        config_parameter='al_field_service.labor_product_id',
    )
    fsm_so_policy = fields.Selection(
        [('manual', 'Manual'), ('auto', 'Automatic')],
        string='Materials / Timesheets → Sales Order',
        config_parameter='al_field_service.so_policy',
        default='manual',
    )
    fsm_require_signature = fields.Boolean(
        config_parameter='al_field_service.require_signature',
        default=True,
    )
    fsm_require_checklist = fields.Boolean(
        config_parameter='al_field_service.require_checklist',
        default=True,
    )
    fsm_auto_invoice_on_done = fields.Boolean(
        config_parameter='al_field_service.auto_invoice_on_done',
        default=False,
    )
    fsm_mail_assigned = fields.Boolean(config_parameter='al_field_service.mail_assigned', default=True)
    fsm_mail_planned = fields.Boolean(config_parameter='al_field_service.mail_planned', default=True)
    fsm_mail_started = fields.Boolean(config_parameter='al_field_service.mail_started', default=True)
    fsm_mail_done = fields.Boolean(config_parameter='al_field_service.mail_done', default=True)
    fsm_mail_installation = fields.Boolean(config_parameter='al_field_service.mail_installation', default=True)
    fsm_warranty_reminder_days = fields.Integer(config_parameter='al_field_service.warranty_reminder_days', default=30)

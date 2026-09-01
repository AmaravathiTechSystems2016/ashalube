from odoo import fields, models
from odoo.exceptions import UserError
from odoo.tools.translate import _


class FsmSignReport(models.TransientModel):
    _name = 'fsm.sign.report'
    _description = 'Sign Field Service Report'

    order_id = fields.Many2one('fsm.order', required=True)
    signed_by = fields.Char(required=True)
    signature = fields.Binary(required=True)

    def action_sign(self):
        self.ensure_one()
        if not self.signature:
            raise UserError(_('Please sign the report.'))
        self.order_id.write({
            'signature': self.signature,
            'signed_by': self.signed_by,
            'signed_on': fields.Datetime.now(),
            'signature_confirmed': True,
        })
        self.order_id.message_post(body=_('Service report has been signed by %s.', self.signed_by))
        return {'type': 'ir.actions.act_window_close'}

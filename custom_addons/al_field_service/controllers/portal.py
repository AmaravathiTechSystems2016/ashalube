from odoo import http
from odoo.http import request
from odoo.addons.portal.controllers.portal import CustomerPortal, pager as portal_pager


class FsmCustomerPortal(CustomerPortal):

    def _prepare_home_portal_values(self, counters):
        values = super()._prepare_home_portal_values(counters)
        if 'fsm_order_count' in counters:
            partner = request.env.user.partner_id
            values['fsm_order_count'] = request.env['fsm.order'].search_count([
                ('partner_id', 'child_of', partner.commercial_partner_id.id),
            ]) if request.env['fsm.order'].has_access('read') else 0
        return values

    @http.route(['/my/fsm', '/my/fsm/page/<int:page>'], type='http', auth='user', website=True)
    def portal_my_fsm(self, page=1, **kw):
        partner = request.env.user.partner_id
        domain = [('partner_id', 'child_of', partner.commercial_partner_id.id)]
        orders = request.env['fsm.order'].search(domain, order='id desc')
        values = {
            'orders': orders,
            'page_name': 'fsm',
        }
        return request.render('al_field_service.portal_my_fsm_orders', values)

    @http.route(['/my/fsm/<int:order_id>'], type='http', auth='public', website=True)
    def portal_fsm_order(self, order_id, access_token=None, **kw):
        order = request.env['fsm.order'].browse(order_id).sudo()
        if access_token:
            order = order.sudo()
            if order.access_token != access_token:
                return request.redirect('/my')
        elif not request.env.user._is_public():
            order = request.env['fsm.order'].browse(order_id)
            order.check_access('read')
        else:
            return request.redirect('/web/login')
        return request.render('al_field_service.portal_fsm_order_page', {'order': order, 'page_name': 'fsm'})

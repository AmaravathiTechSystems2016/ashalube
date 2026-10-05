import json

from odoo import api, models
from odoo.tools import file_open

from .dashboard_builder import build_crm_sales_dashboard


class SpreadsheetDashboard(models.Model):
    _inherit = 'spreadsheet.dashboard'

    @api.model
    def _al_apply_crm_dashboard(self):
        dashboard = self.env.ref(
            'spreadsheet_dashboard_sale.spreadsheet_dashboard_sales',
            raise_if_not_found=False,
        )
        if not dashboard:
            return
        with file_open('spreadsheet_dashboard_sale/data/files/sales_dashboard.json') as handle:
            original = json.load(handle)
        # An empty sales database makes Odoo serve the stock sample file and
        # hide this snapshot. Keep the live dashboard so CRM figures stay visible.
        dashboard.sample_dashboard_file_path = False
        dashboard.spreadsheet_data = json.dumps(build_crm_sales_dashboard(original))

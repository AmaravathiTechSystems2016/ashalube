import { patch } from "@web/core/utils/patch";
import { SpreadsheetDashboardAction } from "@spreadsheet_dashboard/bundle/dashboard_action/dashboard_action";
import { Status } from "@spreadsheet_dashboard/bundle/dashboard_action/dashboard_loader_service";

patch(SpreadsheetDashboardAction.prototype, {
    get crmSheets() {
        const dashboard = this.loader.getActiveDashboard();
        if (!dashboard || dashboard.status !== Status.Loaded || !dashboard.model) {
            return [];
        }
        const getters = dashboard.model.getters;
        const activeId = getters.getActiveSheetId();
        return getters.getVisibleSheetIds().map((id) => ({
            id,
            name: getters.getSheetName(id),
            active: id === activeId,
        }));
    },

    activateCrmSheet(sheetId) {
        const dashboard = this.loader.getActiveDashboard();
        if (!dashboard?.model) {
            return;
        }
        const model = dashboard.model;
        const sheetIdFrom = model.getters.getActiveSheetId();
        if (sheetIdFrom !== sheetId) {
            model.dispatch("ACTIVATE_SHEET", { sheetIdFrom, sheetIdTo: sheetId });
        }
    },
});

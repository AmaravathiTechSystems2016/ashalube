/** @odoo-module **/

import { Component, onWillStart, useState } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { _t } from "@web/core/l10n/translation";

export class FsmGanttAction extends Component {
    static template = "al_field_service.FsmGantt";
    static props = ["*"];

    setup() {
        this.orm = useService("orm");
        this.action = useService("action");
        this.state = useState({ days: [], rows: [], dateFrom: false });
        onWillStart(() => this.load());
    }

    async load(dateFrom) {
        const payload = await this.orm.call("fsm.order", "get_gantt_payload", [dateFrom || false]);
        this.state.days = payload.days;
        this.state.rows = payload.rows;
        this.state.dateFrom = payload.date_from;
    }

    async shift(days) {
        const current = new Date(this.state.dateFrom);
        current.setDate(current.getDate() + days);
        const iso = current.toISOString().slice(0, 19).replace("T", " ");
        await this.load(iso);
    }

    onPrev() {
        this.shift(-7);
    }

    onToday() {
        this.load(false);
    }

    onNext() {
        this.shift(7);
    }

    onBarClick(ev) {
        const id = Number(ev.currentTarget.dataset.id);
        this.openOrder(id);
    }
        this.action.doAction({
            type: "ir.actions.act_window",
            res_model: "fsm.order",
            res_id: id,
            views: [[false, "form"]],
            target: "current",
        });
    }
}

registry.category("actions").add("al_field_service.fsm_gantt", FsmGanttAction);

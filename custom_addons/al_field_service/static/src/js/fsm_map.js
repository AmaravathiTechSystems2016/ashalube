/** @odoo-module **/

import { Component, onWillStart, useState } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";

export class FsmMapAction extends Component {
    static template = "al_field_service.FsmMap";
    static props = ["*"];

    setup() {
        this.orm = useService("orm");
        this.action = useService("action");
        this.state = useState({ pins: [], itineraryUrl: false, selected: false });
        onWillStart(() => this.load());
    }

    async load() {
        const payload = await this.orm.call("fsm.order", "get_map_payload", [[]]);
        this.state.pins = payload.pins;
        this.state.itineraryUrl = payload.itinerary_url;
        this.state.selected = payload.pins[0] || false;
    }

    selectPin(ev) {
        const id = Number(ev.currentTarget.dataset.id);
        this.state.selected = this.state.pins.find((p) => p.id === id) || false;
    }

    openSelected(ev) {
        ev.stopPropagation();
        this.openOrder(Number(ev.currentTarget.dataset.id));
    }

    navigateSelected(ev) {
        ev.stopPropagation();
        const id = Number(ev.currentTarget.dataset.id);
        const pin = this.state.pins.find((p) => p.id === id);
        if (pin) {
            this.navigate(pin);
        }
    }

    osmUrl(pin) {
        if (pin && pin.lat && pin.lng) {
            return `https://www.openstreetmap.org/export/embed.html?bbox=${pin.lng - 0.04}%2C${pin.lat - 0.03}%2C${pin.lng + 0.04}%2C${pin.lat + 0.03}&layer=mapnik&marker=${pin.lat}%2C${pin.lng}`;
        }
        const q = encodeURIComponent((pin && pin.address) || "India");
        return `https://maps.google.com/maps?q=${q}&output=embed`;
    }

    openOrder(id) {
        this.action.doAction({
            type: "ir.actions.act_window",
            res_model: "fsm.order",
            res_id: id,
            views: [[false, "form"]],
            target: "current",
        });
    }

    openItinerary() {
        if (this.state.itineraryUrl) {
            window.open(this.state.itineraryUrl, "_blank");
        }
    }

    navigate(pin) {
        const dest = pin.lat && pin.lng ? `${pin.lat},${pin.lng}` : encodeURIComponent(pin.address || pin.name);
        window.open(`https://www.google.com/maps/dir/?api=1&destination=${dest}&travelmode=driving`, "_blank");
    }
}

registry.category("actions").add("al_field_service.fsm_map", FsmMapAction);

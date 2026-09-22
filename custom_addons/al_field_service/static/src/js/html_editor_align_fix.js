import { AlignPlugin } from "@html_editor/main/align/align_plugin";
import { TableAlignPlugin } from "@html_editor/main/table/table_align_plugin";
import { patch } from "@web/core/utils/patch";
import { reactive } from "@odoo/owl";

patch(AlignPlugin.prototype, {
    updateAlignmentParams() {
        if (!this.alignment) {
            this.alignment = reactive({ displayName: "" });
        }
        return super.updateAlignmentParams();
    },
});

patch(TableAlignPlugin.prototype, {
    updateVerticalAlignParams() {
        if (!this.verticalAlignMode) {
            this.verticalAlignMode = reactive({ displayName: "" });
        }
        return super.updateVerticalAlignParams();
    },
});

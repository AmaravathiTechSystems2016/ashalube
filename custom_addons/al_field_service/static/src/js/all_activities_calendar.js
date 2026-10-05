/** @odoo-module **/

import { registry } from "@web/core/registry";
import { Domain } from "@web/core/domain";
import { serializeDate, serializeDateTime } from "@web/core/l10n/dates";
import { calendarView } from "@web/views/calendar/calendar_view";
import { CalendarModel } from "@web/views/calendar/calendar_model";
import { CalendarController } from "@web/views/calendar/calendar_controller";

const { DateTime } = luxon;

export class AllActivitiesCalendarModel extends CalendarModel {
    get canEdit() {
        if (this.meta.fieldMapping.date_start === "activity_date_deadline") {
            return this.meta.canEdit;
        }
        return super.canEdit;
    }

    async loadRecords(data) {
        const activityOnly = this.meta.fieldMapping.date_start === "activity_date_deadline";
        const baseRecords = activityOnly ? {} : await super.loadRecords(data);
        const activityRecords = await this._loadActivityRecords(data);
        return { ...baseRecords, ...activityRecords };
    }

    async _loadActivityRecords(data) {
        const { context, fieldNames, resModel } = this.meta;
        const start = serializeDate(data.range.start);
        const end = serializeDate(data.range.end);
        const activities = await this.orm.searchRead(
            "mail.activity",
            [
                ["res_model", "=", resModel],
                ["date_deadline", ">=", start],
                ["date_deadline", "<=", end],
            ],
            ["res_id", "res_name", "date_deadline", "summary", "activity_type_id"],
            { context }
        );
        if (!activities.length) {
            return {};
        }
        const resIds = [...new Set(activities.map((activity) => activity.res_id))];
        const parentDomain = Domain.combine(
            [this.meta.domain || [], [["id", "in", resIds]]],
            "AND"
        ).toList(context || {});
        const parents = await this.orm.searchRead(
            resModel,
            parentDomain,
            [...new Set([...fieldNames, ...Object.keys(this.meta.activeFields || {})])],
            { context }
        );
        const parentsById = Object.fromEntries(parents.map((parent) => [parent.id, parent]));
        const dateStart = this.meta.fieldMapping.date_start;
        const dateStop = this.meta.fieldMapping.date_stop;
        const records = {};
        for (const activity of activities) {
            const parent = parentsById[activity.res_id];
            if (!parent || !activity.date_deadline) {
                continue;
            }
            const parentLabel = parent.display_name || parent.name || activity.res_name || "";
            const typeName = activity.activity_type_id?.[1] || "Activity";
            const title = activity.summary
                ? `${typeName}: ${activity.summary} — ${parentLabel}`
                : `${typeName}: ${parentLabel}`;
            const raw = {
                ...parent,
                id: -activity.id,
                display_name: title,
                _activity_id: activity.id,
                _parent_res_id: parent.id,
            };
            if (dateStart === "activity_date_deadline") {
                raw.activity_date_deadline = activity.date_deadline;
            } else {
                const dayStart = DateTime.fromISO(activity.date_deadline).set({
                    hour: 8,
                    minute: 0,
                    second: 0,
                });
                raw[dateStart] = serializeDateTime(dayStart);
                if (dateStop) {
                    raw[dateStop] = serializeDateTime(dayStart.plus({ hours: 1 }));
                }
            }
            records[raw.id] = this.normalizeRecord(raw);
        }
        return records;
    }

    async unlinkRecord(recordId) {
        const record = this.data.records[recordId];
        if (record?.rawRecord?._activity_id) {
            await this.orm.unlink("mail.activity", [record.rawRecord._activity_id]);
            await this.load();
            return;
        }
        return super.unlinkRecord(recordId);
    }

    async updateRecord(record, options = {}) {
        const existing = this.data.records[record.id];
        if (existing?.rawRecord?._activity_id) {
            await this.orm.write("mail.activity", [existing.rawRecord._activity_id], {
                date_deadline: record.start.toISODate(),
            });
            await this.load();
            return;
        }
        return super.updateRecord(record, options);
    }
}

export class AllActivitiesCalendarController extends CalendarController {
    async editRecord(record, context = {}) {
        const stored = this.model.data.records[record.id];
        const parentId = stored?.rawRecord?._parent_res_id;
        if (parentId) {
            record = { ...record, id: parentId };
        }
        return super.editRecord(record, context);
    }
}

registry.category("views").add("all_activities_calendar", {
    ...calendarView,
    Model: AllActivitiesCalendarModel,
    Controller: AllActivitiesCalendarController,
});

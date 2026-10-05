import copy
import json

F_PERIOD = "13d30fda-b14d-4a56-b186-25468af3b1e9"
F_COUNTRY = "e6db018b-19ec-42c3-b29e-11b1e3910916"
F_PRODUCT = "dbb716a1-5977-47ee-a53e-ca5716303433"
F_CUSTOMER = "7d95fe28-fd13-4805-948c-95742e7d6733"
F_CATEGORY = "27e323f4-cd70-4345-82fa-dfc855707bc1"
F_TEAM = "b75963ca-ab5f-4da5-9c90-67526517e5e7"
F_USER = "4181e8e3-2e7e-42be-a88b-f24acb7d03e7"
F_SOURCE = "ec466626-f54a-4955-9611-eaa2719f1afb"
F_MEDIUM = "85d94827-6ce2-429c-9775-ef646cfddb6b"
F_CAMPAIGN = "a7c3e1b2-4d55-4c1a-9f20-6c8e0a11c001"
F_STAGE = "a7c3e1b2-4d55-4c1a-9f20-6c8e0a11c002"
F_TAG = "a7c3e1b2-4d55-4c1a-9f20-6c8e0a11c003"

ENQUIRY_DOMAIN = ["|", ["active", "=", True], ["won_status", "=", "lost"]]
NEGO_DOMAIN = [
    "&", "&",
    ["active", "=", True],
    ["won_status", "=", "pending"],
    "|",
    ["stage_id", "ilike", "Proposition"],
    ["tag_ids", "ilike", "Negotiation"],
]
OPEN_DOMAIN = [["active", "=", True], ["won_status", "=", "pending"]]
WON_DOMAIN = [["won_status", "=", "won"]]
LOST_DOMAIN = [["won_status", "=", "lost"]]
QUOT_DOMAIN = [["state", "in", ["draft", "sent"]]]
QUOT_LINE_DOMAIN = [["state", "in", ["draft", "sent"]], ["display_type", "=", False]]
PO_DOMAIN = [["state", "=", "sale"]]
PO_LINE_DOMAIN = [["state", "=", "sale"], ["display_type", "=", False]]
ACT_DOMAIN = [["res_model", "=", "crm.lead"]]

CTX_ARCHIVED = {"active_test": False}
CRM_VIEWS = [
    [False, "kanban"], [False, "list"], [False, "form"], [False, "pivot"],
    [False, "graph"], [False, "activity"], [False, "calendar"], [False, "search"],
]
SALE_VIEWS = [
    [False, "list"], [False, "kanban"], [False, "form"], [False, "calendar"],
    [False, "pivot"], [False, "graph"], [False, "activity"], [False, "search"],
]
ACT_VIEWS = [
    [False, "list"], [False, "kanban"], [False, "form"], [False, "calendar"],
    [False, "pivot"], [False, "graph"], [False, "search"],
]


def _m2o(chain):
    return {"chain": chain, "type": "many2one"}


def _m2m(chain):
    return {"chain": chain, "type": "many2many"}


def _dt(chain, offset=0, kind="datetime"):
    return {"chain": chain, "type": kind, "offset": offset}


def _lead_match(offset=0, date_chain="create_date"):
    return {
        F_PERIOD: _dt(date_chain, offset),
        F_COUNTRY: _m2o("country_id"),
        F_CUSTOMER: _m2o("partner_id"),
        F_TEAM: _m2o("team_id"),
        F_USER: _m2o("user_id"),
        F_SOURCE: _m2o("source_id"),
        F_MEDIUM: _m2o("medium_id"),
        F_CAMPAIGN: _m2o("campaign_id"),
        F_STAGE: _m2o("stage_id"),
        F_TAG: _m2m("tag_ids"),
    }


def _order_match(offset=0):
    return {
        F_PERIOD: _dt("date_order", offset),
        F_COUNTRY: _m2o("partner_id.country_id"),
        F_PRODUCT: _m2o("order_line.product_id"),
        F_CUSTOMER: _m2o("partner_id"),
        F_CATEGORY: _m2o("order_line.product_id.categ_id"),
        F_TEAM: _m2o("team_id"),
        F_USER: _m2o("user_id"),
        F_SOURCE: _m2o("source_id"),
        F_MEDIUM: _m2o("medium_id"),
        F_CAMPAIGN: _m2o("campaign_id"),
        F_STAGE: _m2o("opportunity_id.stage_id"),
        F_TAG: _m2m("opportunity_id.tag_ids"),
    }


def _line_match(offset=0):
    return {
        F_PERIOD: _dt("order_id.date_order", offset),
        F_COUNTRY: _m2o("order_partner_id.country_id"),
        F_PRODUCT: _m2o("product_id"),
        F_CUSTOMER: _m2o("order_partner_id"),
        F_CATEGORY: _m2o("product_id.categ_id"),
        F_TEAM: _m2o("order_id.team_id"),
        F_USER: _m2o("salesman_id"),
        F_SOURCE: _m2o("order_id.source_id"),
        F_MEDIUM: _m2o("order_id.medium_id"),
        F_CAMPAIGN: _m2o("order_id.campaign_id"),
        F_STAGE: _m2o("order_id.opportunity_id.stage_id"),
        F_TAG: _m2m("order_id.opportunity_id.tag_ids"),
    }


def _activity_match(offset=0):
    return {
        F_PERIOD: _dt("create_date", offset),
        F_USER: _m2o("user_id"),
    }


def _meas(field, label):
    return {
        "id": field,
        "fieldName": field,
        "aggregator": "sum",
        "userDefinedName": label,
    }


def _view_link(title, model, view_type, domain, context, name, views):
    payload = {
        "viewType": view_type,
        "action": {
            "domain": domain,
            "context": context,
            "modelName": model,
            "views": views,
        },
        "threshold": 0,
        "name": name,
    }
    return "[%s](odoo://view/%s)" % (title, json.dumps(payload, separators=(",", ":")))


def _next_id(mapping):
    numbers = [int(key) for key in mapping if str(key).isdigit()]
    return (max(numbers) if numbers else 0) + 1


def _scorecard(fig_id, title, key, baseline, x, y, background, up="#00A04A", down="#DC6965"):
    data = {
        "baselineColorDown": down,
        "baselineColorUp": up,
        "baselineMode": "percentage",
        "title": {"text": title, "bold": True, "color": "#434343"},
        "type": "scorecard",
        "background": background,
        "baseline": baseline,
        "baselineDescr": {"text": "since last period"},
        "keyValue": key,
        "humanize": False,
        "chartId": fig_id,
    }
    return {
        "id": fig_id,
        "width": 208,
        "height": 96,
        "tag": "chart",
        "data": data,
        "offset": {"x": x, "y": y},
        "col": 0,
        "row": 0,
    }


def _chart(fig_id, chart_type, model, measure, group_by, domain, matching, title, x, y, width, height, context=None):
    return {
        "id": fig_id,
        "width": width,
        "height": height,
        "tag": "chart",
        "data": {
            "title": {"text": title, "bold": True, "color": "#01666B"},
            "background": "#FFFFFF",
            "legendPosition": "none",
            "metaData": {
                "groupBy": group_by,
                "measure": measure,
                "order": None,
                "resModel": model,
                "mode": "line" if chart_type == "odoo_line" else "bar",
                "cumulatedStart": False,
            },
            "searchParams": {
                "comparison": None,
                "context": context or {"group_by": []},
                "domain": domain,
                "groupBy": group_by,
                "orderBy": [],
            },
            "type": chart_type,
            "dataSets": [{}],
            "verticalAxisPosition": "left",
            "stacked": False,
            "fillArea": chart_type == "odoo_line",
            "cumulatedStart": False,
            "chartId": fig_id,
            "fieldMatching": matching,
        },
        "offset": {"x": x, "y": y},
        "col": 0,
        "row": 0,
    }


def _pivot(key, model, name, domain, measures, matching, rows=None, columns=None, context=None, action=None, sorted_measure=None):
    pivot = {
        "type": "ODOO",
        "fieldMatching": matching,
        "context": context or {},
        "domain": domain,
        "id": key,
        "measures": measures,
        "model": model,
        "name": name,
        "sortedColumn": (
            {"measure": sorted_measure, "order": "desc", "domain": []}
            if sorted_measure else None
        ),
        "formulaId": key,
        "columns": columns or [],
        "rows": rows or [],
    }
    if action:
        pivot["actionXmlId"] = action
    return pivot


def _list(key, model, name, domain, columns, order, matching, context=None, action=None):
    record = {
        "columns": columns,
        "domain": domain,
        "model": model,
        "context": context or {},
        "orderBy": order,
        "id": key,
        "name": name,
        "fieldMatching": matching,
    }
    if action:
        record["actionXmlId"] = action
    return record


def _blank_sheet(sheet_id, name, cells, figures, rows, cols, col_number, row_number, styles):
    return {
        "id": sheet_id,
        "name": name,
        "colNumber": col_number,
        "rowNumber": row_number,
        "rows": rows,
        "cols": cols,
        "merges": [],
        "cells": cells,
        "styles": styles,
        "formats": {},
        "borders": {},
        "conditionalFormats": [],
        "dataValidationRules": [],
        "figures": figures,
        "tables": [],
        "areGridLinesVisible": True,
        "isVisible": True,
        "headerGroups": {"ROW": [], "COL": []},
        "comments": {},
    }


def _row_sizes(extra):
    rows = {str(index): {"size": 23} for index in range(27)}
    rows.update(extra)
    return rows


def _list_block(cells, styles, row, list_id, title, link, columns, letters):
    cells["%s%s" % (letters[0], row)] = link
    styles["%s%s:%s%s" % (letters[0], row, letters[-1], row)] = 1
    header = row + 1
    for letter, (field, label) in zip(letters, columns):
        if label:
            cells["%s%s" % (letter, header)] = '=ODOO.LIST.HEADER(%s,"%s",_t("%s"))' % (list_id, field, label)
        else:
            cells["%s%s" % (letter, header)] = '=ODOO.LIST.HEADER(%s,"%s")' % (list_id, field)
        for index in range(1, 11):
            cells["%s%s" % (letter, header + index)] = '=ODOO.LIST(%s,%s,"%s")' % (list_id, index, field)
    styles["%s%s:%s%s" % (letters[0], header, letters[-1], header)] = 4
    styles["%s%s:%s%s" % (letters[0], header + 1, letters[-1], header + 10)] = 5
    return header + 12


def _extend_existing_filters(data):
    campaign_chain = {
        "sale.report": "campaign_id",
        "sale.order": "campaign_id",
        "crm.lead": "campaign_id",
        "sale.order.line": "order_id.campaign_id",
    }

    def extend(matching, model):
        if not isinstance(matching, dict) or not model:
            return
        chain = campaign_chain.get(model)
        if chain and F_CAMPAIGN not in matching:
            matching[F_CAMPAIGN] = _m2o(chain)
        if model == "sale.order":
            matching.setdefault(F_STAGE, _m2o("opportunity_id.stage_id"))
            matching.setdefault(F_TAG, _m2m("opportunity_id.tag_ids"))
        elif model == "sale.order.line":
            matching.setdefault(F_STAGE, _m2o("order_id.opportunity_id.stage_id"))
            matching.setdefault(F_TAG, _m2m("order_id.opportunity_id.tag_ids"))
        elif model == "crm.lead":
            matching.setdefault(F_STAGE, _m2o("stage_id"))
            matching.setdefault(F_TAG, _m2m("tag_ids"))

    for pivot in data.get("pivots", {}).values():
        extend(pivot.get("fieldMatching"), pivot.get("model"))
    for record in data.get("lists", {}).values():
        extend(record.get("fieldMatching"), record.get("model"))
    for sheet in data.get("sheets", []):
        for figure in sheet.get("figures", []):
            figure_data = figure.get("data") or {}
            if figure.get("tag") == "chart":
                model = (figure_data.get("metaData") or {}).get("resModel")
                extend(figure_data.get("fieldMatching"), model)
            elif figure.get("tag") == "carousel":
                definitions = figure_data.get("chartDefinitions") or {}
                matching = figure_data.get("fieldMatching") or {}
                for chart_id, chart in definitions.items():
                    model = (chart.get("metaData") or {}).get("resModel")
                    if isinstance(matching.get(chart_id), dict):
                        extend(matching[chart_id], model)


def _add_filters(data):
    present = {item["id"] for item in data.get("globalFilters", [])}
    extras = [
        {
            "id": F_CAMPAIGN,
            "type": "relation",
            "label": "Campaign",
            "modelName": "utm.campaign",
            "defaultValueDisplayNames": [],
        },
        {
            "id": F_STAGE,
            "type": "relation",
            "label": "Stage",
            "modelName": "crm.stage",
            "defaultValueDisplayNames": [],
        },
        {
            "id": F_TAG,
            "type": "relation",
            "label": "Tag",
            "modelName": "crm.tag",
            "defaultValueDisplayNames": [],
        },
    ]
    for item in extras:
        if item["id"] not in present:
            data["globalFilters"].append(item)


def _kpi_cells(data_sheet, ids):
    cells = data_sheet["cells"]
    specs = [
        (11, "Enquiries", '=PIVOT.VALUE(%s,"__count")' % ids["enquiry"], '=PIVOT.VALUE(%s,"__count")' % ids["enquiry_prev"]),
        (12, "Enquiry revenue", '=PIVOT.VALUE(%s,"expected_revenue")' % ids["enquiry"], '=PIVOT.VALUE(%s,"expected_revenue")' % ids["enquiry_prev"]),
        (13, "Quotations", '=PIVOT.VALUE(%s,"__count")' % ids["quot"], '=PIVOT.VALUE(%s,"__count")' % ids["quot_prev"]),
        (14, "Quotation quantity", '=PIVOT.VALUE(%s,"product_uom_qty")' % ids["quot_line"], '=PIVOT.VALUE(%s,"product_uom_qty")' % ids["quot_line_prev"]),
        (15, "Quotation revenue", '=PIVOT.VALUE(%s,"price_subtotal")' % ids["quot_line"], '=PIVOT.VALUE(%s,"price_subtotal")' % ids["quot_line_prev"]),
        (16, "Negotiations", '=PIVOT.VALUE(%s,"expected_revenue")' % ids["nego"], '=PIVOT.VALUE(%s,"expected_revenue")' % ids["nego_prev"]),
        (17, "Negotiation count", '=PIVOT.VALUE(%s,"__count")' % ids["nego"], '=PIVOT.VALUE(%s,"__count")' % ids["nego_prev"]),
        (18, "Won", '=PIVOT.VALUE(%s,"__count")' % ids["won"], '=PIVOT.VALUE(%s,"__count")' % ids["won_prev"]),
        (19, "Won revenue", '=PIVOT.VALUE(%s,"expected_revenue")' % ids["won"], '=PIVOT.VALUE(%s,"expected_revenue")' % ids["won_prev"]),
        (20, "Lost", '=PIVOT.VALUE(%s,"__count")' % ids["lost"], '=PIVOT.VALUE(%s,"__count")' % ids["lost_prev"]),
        (21, "Lost revenue", '=PIVOT.VALUE(%s,"expected_revenue")' % ids["lost"], '=PIVOT.VALUE(%s,"expected_revenue")' % ids["lost_prev"]),
        (22, "Purchase orders", '=PIVOT.VALUE(%s,"__count")' % ids["po"], '=PIVOT.VALUE(%s,"__count")' % ids["po_prev"]),
        (23, "Purchase order quantity", '=PIVOT.VALUE(%s,"product_uom_qty")' % ids["po_line"], '=PIVOT.VALUE(%s,"product_uom_qty")' % ids["po_line_prev"]),
        (24, "Purchase order revenue", '=PIVOT.VALUE(%s,"price_subtotal")' % ids["po_line"], '=PIVOT.VALUE(%s,"price_subtotal")' % ids["po_line_prev"]),
        (25, "Follow-ups", '=PIVOT.VALUE(%s,"__count")' % ids["activity"], '=PIVOT.VALUE(%s,"__count")' % ids["activity_prev"]),
        (26, "Win rate %", "=IFERROR(B18/(B18+B20)*100,0)", "=IFERROR(C18/(C18+C20)*100,0)"),
        (27, "Average enquiry", "=IFERROR(B12/B11,0)", "=IFERROR(C12/C11,0)"),
        (28, "Open pipeline", '=PIVOT.VALUE(%s,"expected_revenue")' % ids["open"], '=PIVOT.VALUE(%s,"expected_revenue")' % ids["open_prev"]),
    ]
    cells["A10"] = '=_t("CRM")'
    cells["B10"] = '=_t("Current")'
    cells["C10"] = '=_t("Previous")'
    for row, label, current, previous in specs:
        cells["A%s" % row] = '=_t("%s")' % label
        cells["B%s" % row] = current
        cells["C%s" % row] = previous
        cells["D%s" % row] = "=FORMAT.LARGE.NUMBER(B%s)" % row
        cells["E%s" % row] = "=FORMAT.LARGE.NUMBER(C%s)" % row
    styles = data_sheet.setdefault("styles", {})
    styles["A10:E10"] = 8
    styles["D11:E28"] = 9


def _cards(prefix, origin_y, specs):
    figures = []
    for index, (title, key, baseline, background, up, down) in enumerate(specs):
        figures.append(_scorecard(
            "%s-%s" % (prefix, index),
            title,
            key,
            baseline,
            index * 218,
            origin_y,
            background,
            up,
            down,
        ))
    return figures


def _standard_cols():
    return {
        "0": {"size": 220},
        "1": {"size": 160},
        "2": {"size": 150},
        "3": {"size": 150},
        "4": {"size": 220},
        "5": {"size": 160},
        "6": {"size": 150},
    }


def build_crm_sales_dashboard(original):
    data = copy.deepcopy(original)
    _add_filters(data)
    _extend_existing_filters(data)

    pivot_seq = _next_id(data["pivots"])
    list_seq = _next_id(data["lists"])
    ids = {}

    def add_pivot(name, **kwargs):
        nonlocal pivot_seq
        key = str(pivot_seq)
        data["pivots"][key] = _pivot(key, name=name, **kwargs)
        pivot_seq += 1
        return key

    def add_list(name, **kwargs):
        nonlocal list_seq
        key = str(list_seq)
        data["lists"][key] = _list(key, name=name, **kwargs)
        list_seq += 1
        return key

    count_rev = [_meas("__count", "Quantity"), _meas("expected_revenue", "Revenue")]
    qty_rev = [_meas("product_uom_qty", "Quantity"), _meas("price_subtotal", "Revenue")]

    ids["enquiry"] = add_pivot("CRM enquiries", model="crm.lead", domain=ENQUIRY_DOMAIN, measures=count_rev, matching=_lead_match(0), context=CTX_ARCHIVED, action="crm.crm_lead_action_pipeline")
    ids["enquiry_prev"] = add_pivot("CRM enquiries previous", model="crm.lead", domain=ENQUIRY_DOMAIN, measures=count_rev, matching=_lead_match(-1), context=CTX_ARCHIVED, action="crm.crm_lead_action_pipeline")
    ids["nego"] = add_pivot("CRM negotiations", model="crm.lead", domain=NEGO_DOMAIN, measures=count_rev, matching=_lead_match(0), action="crm.crm_lead_action_pipeline")
    ids["nego_prev"] = add_pivot("CRM negotiations previous", model="crm.lead", domain=NEGO_DOMAIN, measures=count_rev, matching=_lead_match(-1), action="crm.crm_lead_action_pipeline")
    ids["won"] = add_pivot("CRM won", model="crm.lead", domain=WON_DOMAIN, measures=count_rev, matching=_lead_match(0, "date_closed"), action="crm.crm_lead_action_pipeline")
    ids["won_prev"] = add_pivot("CRM won previous", model="crm.lead", domain=WON_DOMAIN, measures=count_rev, matching=_lead_match(-1, "date_closed"), action="crm.crm_lead_action_pipeline")
    ids["lost"] = add_pivot("CRM lost", model="crm.lead", domain=LOST_DOMAIN, measures=count_rev, matching=_lead_match(0, "date_closed"), context=CTX_ARCHIVED, action="crm.crm_lead_action_pipeline")
    ids["lost_prev"] = add_pivot("CRM lost previous", model="crm.lead", domain=LOST_DOMAIN, measures=count_rev, matching=_lead_match(-1, "date_closed"), context=CTX_ARCHIVED, action="crm.crm_lead_action_pipeline")
    ids["quot"] = add_pivot("CRM quotations", model="sale.order", domain=QUOT_DOMAIN, measures=[_meas("__count", "Quantity")], matching=_order_match(0), action="sale.action_quotations")
    ids["quot_prev"] = add_pivot("CRM quotations previous", model="sale.order", domain=QUOT_DOMAIN, measures=[_meas("__count", "Quantity")], matching=_order_match(-1), action="sale.action_quotations")
    ids["quot_line"] = add_pivot("CRM quotation lines", model="sale.order.line", domain=QUOT_LINE_DOMAIN, measures=qty_rev, matching=_line_match(0), action="sale.action_quotations")
    ids["quot_line_prev"] = add_pivot("CRM quotation lines previous", model="sale.order.line", domain=QUOT_LINE_DOMAIN, measures=qty_rev, matching=_line_match(-1), action="sale.action_quotations")
    ids["po"] = add_pivot("CRM purchase orders", model="sale.order", domain=PO_DOMAIN, measures=[_meas("__count", "Quantity")], matching=_order_match(0), action="sale.action_orders")
    ids["po_prev"] = add_pivot("CRM purchase orders previous", model="sale.order", domain=PO_DOMAIN, measures=[_meas("__count", "Quantity")], matching=_order_match(-1), action="sale.action_orders")
    ids["po_line"] = add_pivot("CRM purchase order lines", model="sale.order.line", domain=PO_LINE_DOMAIN, measures=qty_rev, matching=_line_match(0), action="sale.action_orders")
    ids["po_line_prev"] = add_pivot("CRM purchase order lines previous", model="sale.order.line", domain=PO_LINE_DOMAIN, measures=qty_rev, matching=_line_match(-1), action="sale.action_orders")
    ids["activity"] = add_pivot("CRM follow-ups", model="mail.activity", domain=ACT_DOMAIN, measures=[_meas("__count", "Quantity")], matching=_activity_match(0), action="mail.mail_activity_action")
    ids["activity_prev"] = add_pivot("CRM follow-ups previous", model="mail.activity", domain=ACT_DOMAIN, measures=[_meas("__count", "Quantity")], matching=_activity_match(-1), action="mail.mail_activity_action")
    ids["open"] = add_pivot("CRM open pipeline", model="crm.lead", domain=OPEN_DOMAIN, measures=count_rev, matching=_lead_match(0), action="crm.crm_lead_action_pipeline")
    ids["open_prev"] = add_pivot("CRM open pipeline previous", model="crm.lead", domain=OPEN_DOMAIN, measures=count_rev, matching=_lead_match(-1), action="crm.crm_lead_action_pipeline")

    ids["stage"] = add_pivot(
        "Pipeline by stage", model="crm.lead", domain=OPEN_DOMAIN, measures=count_rev,
        matching=_lead_match(0), columns=[{"fieldName": "stage_id"}], action="crm.crm_lead_action_pipeline",
    )
    ids["salespeople"] = add_pivot(
        "CRM salespeople", model="crm.lead", domain=OPEN_DOMAIN, measures=count_rev,
        matching=_lead_match(0), rows=[{"fieldName": "user_id"}], sorted_measure="expected_revenue",
        action="crm.crm_lead_action_pipeline",
    )
    ids["sources"] = add_pivot(
        "CRM sources", model="crm.lead", domain=ENQUIRY_DOMAIN, measures=count_rev,
        matching=_lead_match(0), rows=[{"fieldName": "source_id"}], sorted_measure="expected_revenue",
        context=CTX_ARCHIVED, action="crm.crm_opportunity_report_action",
    )
    ids["reasons"] = add_pivot(
        "CRM lost reasons", model="crm.lead", domain=LOST_DOMAIN, measures=count_rev,
        matching=_lead_match(0, "date_closed"), rows=[{"fieldName": "lost_reason_id"}],
        sorted_measure="__count", context=CTX_ARCHIVED, action="crm.crm_lead_action_pipeline",
    )
    ids["teams"] = add_pivot(
        "CRM teams", model="crm.lead", domain=OPEN_DOMAIN, measures=count_rev,
        matching=_lead_match(0), rows=[{"fieldName": "team_id"}], sorted_measure="expected_revenue",
        action="crm.crm_lead_action_pipeline",
    )
    ids["countries"] = add_pivot(
        "CRM countries", model="crm.lead", domain=ENQUIRY_DOMAIN, measures=count_rev,
        matching=_lead_match(0), rows=[{"fieldName": "country_id"}], sorted_measure="expected_revenue",
        context=CTX_ARCHIVED, action="crm.crm_opportunity_report_action",
    )
    ids["quot_products"] = add_pivot(
        "Quotation products", model="sale.order.line", domain=QUOT_LINE_DOMAIN, measures=qty_rev,
        matching=_line_match(0), rows=[{"fieldName": "product_id"}], sorted_measure="price_subtotal",
        action="sale.action_quotations",
    )
    ids["po_products"] = add_pivot(
        "Purchase order products", model="sale.order.line", domain=PO_LINE_DOMAIN, measures=qty_rev,
        matching=_line_match(0), rows=[{"fieldName": "product_id"}], sorted_measure="price_subtotal",
        action="sale.action_orders",
    )
    ids["act_type"] = add_pivot(
        "Follow-up types", model="mail.activity", domain=ACT_DOMAIN, measures=[_meas("__count", "Quantity")],
        matching=_activity_match(0), rows=[{"fieldName": "activity_type_id"}], sorted_measure="__count",
        action="mail.mail_activity_action",
    )
    ids["act_user"] = add_pivot(
        "Follow-up users", model="mail.activity", domain=ACT_DOMAIN, measures=[_meas("__count", "Quantity")],
        matching=_activity_match(0), rows=[{"fieldName": "user_id"}], sorted_measure="__count",
        action="mail.mail_activity_action",
    )
    ids["won_user"] = add_pivot(
        "Won by salesperson", model="crm.lead", domain=WON_DOMAIN, measures=count_rev,
        matching=_lead_match(0, "date_closed"), rows=[{"fieldName": "user_id"}],
        sorted_measure="expected_revenue", action="crm.crm_lead_action_pipeline",
    )

    ids["list_enquiry"] = add_list(
        "Top enquiries", model="crm.lead", domain=ENQUIRY_DOMAIN,
        columns=["name", "partner_id", "user_id", "stage_id", "expected_revenue"],
        order=[{"name": "expected_revenue", "asc": False}],
        matching=_lead_match(0), context=CTX_ARCHIVED, action="crm.crm_lead_action_pipeline",
    )
    ids["list_won"] = add_list(
        "Won opportunities", model="crm.lead", domain=WON_DOMAIN,
        columns=["name", "partner_id", "user_id", "expected_revenue", "date_closed"],
        order=[{"name": "expected_revenue", "asc": False}],
        matching=_lead_match(0, "date_closed"), action="crm.crm_lead_action_pipeline",
    )
    ids["list_lost"] = add_list(
        "Lost opportunities", model="crm.lead", domain=LOST_DOMAIN,
        columns=["name", "partner_id", "user_id", "lost_reason_id", "expected_revenue"],
        order=[{"name": "expected_revenue", "asc": False}],
        matching=_lead_match(0, "date_closed"), context=CTX_ARCHIVED, action="crm.crm_lead_action_pipeline",
    )
    ids["list_po"] = add_list(
        "Purchase orders", model="sale.order", domain=PO_DOMAIN,
        columns=["name", "partner_id", "user_id", "amount_untaxed"],
        order=[{"name": "amount_untaxed", "asc": False}],
        matching=_order_match(0), action="sale.action_orders",
    )
    ids["list_act"] = add_list(
        "Follow-ups", model="mail.activity", domain=ACT_DOMAIN,
        columns=["res_name", "activity_type_id", "user_id", "date_deadline", "summary"],
        order=[{"name": "date_deadline", "asc": True}],
        matching=_activity_match(0), action="mail.mail_activity_action",
    )

    data["pivotNextId"] = pivot_seq
    data["listNextId"] = list_seq

    data_sheet = next(sheet for sheet in data["sheets"] if sheet["name"] == "Data")
    _kpi_cells(data_sheet, ids)
    data_sheet["isVisible"] = False

    blue, sand, green, red, violet, mint = "#EFF6FF", "#FFF7ED", "#ECFDF5", "#FEF2F2", "#F5F3FF", "#F0FDFA"
    crm_cards = []
    crm_cards += _cards("crm-r1", 8, [
        ("No. of Enquiries", "Data!D11", "Data!E11", blue, "#00A04A", "#DC6965"),
        ("Enquiry Revenue", "Data!D12", "Data!E12", sand, "#00A04A", "#DC6965"),
        ("Quotations", "Data!D13", "Data!E13", blue, "#00A04A", "#DC6965"),
        ("Quotation Qty", "Data!D14", "Data!E14", blue, "#00A04A", "#DC6965"),
        ("Quotation Revenue", "Data!D15", "Data!E15", sand, "#00A04A", "#DC6965"),
    ])
    crm_cards += _cards("crm-r2", 112, [
        ("Negotiations", "Data!D16", "Data!E16", violet, "#00A04A", "#DC6965"),
        ("Total Won", "Data!D18", "Data!E18", green, "#00A04A", "#DC6965"),
        ("Total Lost", "Data!D20", "Data!E20", red, "#DC6965", "#00A04A"),
        ("Purchase Orders", "Data!D22", "Data!E22", blue, "#00A04A", "#DC6965"),
        ("Follow-ups", "Data!D25", "Data!E25", mint, "#00A04A", "#DC6965"),
    ])
    crm_cards += _cards("crm-r3", 216, [
        ("Win Rate %", "Data!D26", "Data!E26", green, "#00A04A", "#DC6965"),
        ("Avg Enquiry", "Data!D27", "Data!E27", sand, "#00A04A", "#DC6965"),
        ("Open Pipeline", "Data!D28", "Data!E28", violet, "#00A04A", "#DC6965"),
        ("Won Revenue", "Data!D19", "Data!E19", green, "#00A04A", "#DC6965"),
        ("Lost Revenue", "Data!D21", "Data!E21", red, "#DC6965", "#00A04A"),
    ])
    crm_cards.append(_chart(
        "crm-monthly", "odoo_line", "crm.lead", "expected_revenue", ["create_date:month"],
        ENQUIRY_DOMAIN, _lead_match(0), "Enquiry revenue by month",
        0, 328, 640, 260, CTX_ARCHIVED,
    ))
    crm_cards.append(_chart(
        "crm-stages", "odoo_bar", "crm.lead", "expected_revenue", ["stage_id"],
        OPEN_DOMAIN, _lead_match(0), "Proposition column — negotiation value",
        656, 328, 430, 260,
    ))

    crm_cells, crm_styles = {}, {}
    crm_cells["A28"] = _view_link(
        "Pipeline by Stage", "crm.lead", "pivot", OPEN_DOMAIN,
        {"group_by": ["stage_id"], "pivot_measures": ["__count", "expected_revenue"], "pivot_row_groupby": ["stage_id"], "pivot_column_groupby": []},
        "Pipeline", CRM_VIEWS,
    )
    crm_cells["A29"] = "=PIVOT(%s)" % ids["stage"]
    crm_styles["A28:G28"] = 1
    crm_cells["A36"] = _view_link(
        "Top Enquiries", "crm.lead", "list", ENQUIRY_DOMAIN,
        {"group_by": ["user_id"], "active_test": False}, "Enquiries", CRM_VIEWS,
    )
    _list_block(crm_cells, crm_styles, 36, ids["list_enquiry"], "Top Enquiries", crm_cells["A36"], [
        ("partner_id", "Customer"), ("user_id", "Salesperson"), ("expected_revenue", "Revenue"),
    ], ["A", "B", "C"])
    crm_cells["E36"] = _view_link(
        "Top Quotations", "sale.order", "list", QUOT_DOMAIN,
        {"group_by": ["user_id"]}, "Quotations", SALE_VIEWS,
    )
    _list_block(crm_cells, crm_styles, 36, "1", "Top Quotations", crm_cells["E36"], [
        ("partner_id", "Customer"), ("user_id", "Salesperson"), ("amount_untaxed", "Revenue"),
    ], ["E", "F", "G"])
    crm_cells["A50"] = _view_link(
        "Top Salespeople", "crm.lead", "pivot", OPEN_DOMAIN,
        {"group_by": ["user_id"], "pivot_row_groupby": ["user_id"], "pivot_measures": ["__count", "expected_revenue"]},
        "Pipeline", CRM_VIEWS,
    )
    crm_cells["A51"] = "=PIVOT(%s,10,FALSE,FALSE)" % ids["salespeople"]
    crm_styles["A50:C50"] = 1
    crm_cells["E50"] = _view_link(
        "Top Sources", "crm.lead", "pivot", ENQUIRY_DOMAIN,
        {"group_by": ["source_id"], "active_test": False, "pivot_row_groupby": ["source_id"], "pivot_measures": ["__count", "expected_revenue"]},
        "Pipeline Analysis", CRM_VIEWS,
    )
    crm_cells["E51"] = "=PIVOT(%s,10,FALSE,FALSE)" % ids["sources"]
    crm_styles["E50:G50"] = 1
    crm_cells["A64"] = _view_link(
        "Top Sales Teams", "crm.lead", "pivot", OPEN_DOMAIN,
        {"group_by": ["team_id"], "pivot_row_groupby": ["team_id"], "pivot_measures": ["__count", "expected_revenue"]},
        "Pipeline", CRM_VIEWS,
    )
    crm_cells["A65"] = "=PIVOT(%s,10,FALSE,FALSE)" % ids["teams"]
    crm_styles["A64:C64"] = 1
    crm_cells["E64"] = _view_link(
        "Lost Reasons", "crm.lead", "pivot", LOST_DOMAIN,
        {"group_by": ["lost_reason_id"], "active_test": False, "pivot_row_groupby": ["lost_reason_id"], "pivot_measures": ["__count", "expected_revenue"]},
        "Lost", CRM_VIEWS,
    )
    crm_cells["E65"] = "=PIVOT(%s,10,FALSE,FALSE)" % ids["reasons"]
    crm_styles["E64:G64"] = 1
    crm_cells["A78"] = _view_link(
        "Top Countries", "crm.lead", "pivot", ENQUIRY_DOMAIN,
        {"group_by": ["country_id"], "active_test": False, "pivot_row_groupby": ["country_id"], "pivot_measures": ["__count", "expected_revenue"]},
        "Pipeline Analysis", CRM_VIEWS,
    )
    crm_cells["A79"] = "=PIVOT(%s,10,FALSE,FALSE)" % ids["countries"]
    crm_styles["A78:C78"] = 1
    crm_cells["E78"] = _view_link(
        "Quotation Products", "sale.order.line", "pivot", QUOT_LINE_DOMAIN,
        {"group_by": ["product_id"], "pivot_row_groupby": ["product_id"], "pivot_measures": ["product_uom_qty", "price_subtotal"]},
        "Quotations", SALE_VIEWS,
    )
    crm_cells["E79"] = "=PIVOT(%s,10,FALSE,FALSE)" % ids["quot_products"]
    crm_styles["E78:G78"] = 1

    crm_rows = _row_sizes({"27": {"size": 36}, "28": {"size": 34}, "36": {"size": 36}, "50": {"size": 36}, "64": {"size": 36}, "78": {"size": 36}})
    for row in list(range(37, 48)) + list(range(51, 62)) + list(range(65, 76)) + list(range(79, 90)):
        crm_rows[str(row)] = {"size": 28}
    crm_sheet = _blank_sheet("sheet_crm", "CRM", crm_cells, crm_cards, crm_rows, _standard_cols(), 8, 96, crm_styles)

    won_figures = _cards("won", 8, [
        ("Total Won", "Data!D18", "Data!E18", green, "#00A04A", "#DC6965"),
        ("Won Revenue", "Data!D19", "Data!E19", sand, "#00A04A", "#DC6965"),
    ])
    won_figures.append(_chart(
        "won-user", "odoo_bar", "crm.lead", "expected_revenue", ["user_id"],
        WON_DOMAIN, _lead_match(0, "date_closed"), "Won revenue by salesperson",
        450, 8, 620, 250,
    ))
    won_figures.append(_chart(
        "won-month", "odoo_line", "crm.lead", "expected_revenue", ["date_closed:month"],
        WON_DOMAIN, _lead_match(0, "date_closed"), "Won revenue by month",
        0, 270, 1070, 250,
    ))
    won_cells, won_styles = {}, {}
    won_cells["A24"] = _view_link(
        "Won Opportunities", "crm.lead", "list", WON_DOMAIN,
        {"group_by": ["user_id"], "search_default_filter_won_status_won": 1}, "Won", CRM_VIEWS,
    )
    _list_block(won_cells, won_styles, 24, ids["list_won"], "Won", won_cells["A24"], [
        ("name", "Opportunity"), ("partner_id", "Customer"), ("user_id", "Salesperson"),
        ("expected_revenue", "Revenue"), ("date_closed", "Closed"),
    ], ["A", "B", "C", "D", "E"])
    won_cells["A40"] = _view_link(
        "Won by Salesperson", "crm.lead", "pivot", WON_DOMAIN,
        {"group_by": ["user_id"], "pivot_row_groupby": ["user_id"], "pivot_measures": ["__count", "expected_revenue"]},
        "Won", CRM_VIEWS,
    )
    won_cells["A41"] = "=PIVOT(%s,10,FALSE,FALSE)" % ids["won_user"]
    won_styles["A40:C40"] = 1
    won_rows = _row_sizes({"24": {"size": 36}, "40": {"size": 36}})
    for row in range(25, 36):
        won_rows[str(row)] = {"size": 28}
    won_sheet = _blank_sheet("sheet_won", "Total Won", won_cells, won_figures, won_rows, _standard_cols(), 8, 60, won_styles)

    lost_figures = _cards("lost", 8, [
        ("Total Lost", "Data!D20", "Data!E20", red, "#DC6965", "#00A04A"),
        ("Lost Revenue", "Data!D21", "Data!E21", sand, "#DC6965", "#00A04A"),
    ])
    lost_figures.append(_chart(
        "lost-reason", "odoo_bar", "crm.lead", "expected_revenue", ["lost_reason_id"],
        LOST_DOMAIN, _lead_match(0, "date_closed"), "Lost value by reason",
        450, 8, 620, 250, CTX_ARCHIVED,
    ))
    lost_figures.append(_chart(
        "lost-month", "odoo_line", "crm.lead", "__count", ["date_closed:month"],
        LOST_DOMAIN, _lead_match(0, "date_closed"), "Lost opportunities by month",
        0, 270, 1070, 250, CTX_ARCHIVED,
    ))
    lost_cells, lost_styles = {}, {}
    lost_cells["A24"] = _view_link(
        "Lost Opportunities", "crm.lead", "list", LOST_DOMAIN,
        {"group_by": ["lost_reason_id"], "active_test": False, "search_default_filter_won_status_lost": 1},
        "Lost", CRM_VIEWS,
    )
    _list_block(lost_cells, lost_styles, 24, ids["list_lost"], "Lost", lost_cells["A24"], [
        ("name", "Opportunity"), ("partner_id", "Customer"), ("user_id", "Salesperson"),
        ("lost_reason_id", "Lost Reason"), ("expected_revenue", "Revenue"),
    ], ["A", "B", "C", "D", "E"])
    lost_cells["A40"] = _view_link(
        "Lost Reasons", "crm.lead", "pivot", LOST_DOMAIN,
        {"group_by": ["lost_reason_id"], "active_test": False, "pivot_row_groupby": ["lost_reason_id"], "pivot_measures": ["__count", "expected_revenue"]},
        "Lost", CRM_VIEWS,
    )
    lost_cells["A41"] = "=PIVOT(%s,10,FALSE,FALSE)" % ids["reasons"]
    lost_styles["A40:C40"] = 1
    lost_rows = _row_sizes({"24": {"size": 36}, "40": {"size": 36}})
    for row in range(25, 36):
        lost_rows[str(row)] = {"size": 28}
    lost_sheet = _blank_sheet("sheet_lost", "Total Lost", lost_cells, lost_figures, lost_rows, _standard_cols(), 8, 60, lost_styles)

    po_figures = _cards("po", 8, [
        ("Purchase Orders", "Data!D22", "Data!E22", blue, "#00A04A", "#DC6965"),
        ("Total Quantity", "Data!D23", "Data!E23", blue, "#00A04A", "#DC6965"),
        ("Revenue", "Data!D24", "Data!E24", sand, "#00A04A", "#DC6965"),
    ])
    po_figures.append(_chart(
        "po-month", "odoo_line", "sale.order", "amount_untaxed", ["date_order:month"],
        PO_DOMAIN, _order_match(0), "Purchase order revenue by month",
        0, 120, 640, 250,
    ))
    po_figures.append(_chart(
        "po-product", "odoo_bar", "sale.order.line", "product_uom_qty", ["product_id"],
        PO_LINE_DOMAIN, _line_match(0), "Purchase order quantity by product",
        656, 120, 430, 250,
    ))
    po_cells, po_styles = {}, {}
    po_cells["A18"] = _view_link(
        "Purchase Orders", "sale.order", "list", PO_DOMAIN,
        {"group_by": ["user_id"]}, "Purchase Orders", SALE_VIEWS,
    )
    _list_block(po_cells, po_styles, 18, ids["list_po"], "Purchase Orders", po_cells["A18"], [
        ("name", "Order"), ("partner_id", "Customer"), ("user_id", "Salesperson"), ("amount_untaxed", "Revenue"),
    ], ["A", "B", "C", "D"])
    po_cells["A34"] = _view_link(
        "Products", "sale.order.line", "pivot", PO_LINE_DOMAIN,
        {"group_by": ["product_id"], "pivot_row_groupby": ["product_id"], "pivot_measures": ["product_uom_qty", "price_subtotal"]},
        "Purchase Orders", SALE_VIEWS,
    )
    po_cells["A35"] = "=PIVOT(%s,10,FALSE,FALSE)" % ids["po_products"]
    po_styles["A34:C34"] = 1
    po_rows = _row_sizes({"18": {"size": 36}, "34": {"size": 36}})
    for row in range(19, 30):
        po_rows[str(row)] = {"size": 28}
    po_sheet = _blank_sheet("sheet_po", "Purchase Orders", po_cells, po_figures, po_rows, _standard_cols(), 8, 56, po_styles)

    act_figures = _cards("act", 8, [
        ("Follow-ups", "Data!D25", "Data!E25", mint, "#00A04A", "#DC6965"),
    ])
    act_figures.append(_chart(
        "act-type", "odoo_bar", "mail.activity", "__count", ["activity_type_id"],
        ACT_DOMAIN, _activity_match(0), "Follow-ups by type",
        230, 8, 420, 240,
    ))
    act_figures.append(_chart(
        "act-user", "odoo_bar", "mail.activity", "__count", ["user_id"],
        ACT_DOMAIN, _activity_match(0), "Follow-ups by salesperson",
        660, 8, 420, 240,
    ))
    act_cells, act_styles = {}, {}
    act_cells["A14"] = _view_link(
        "Open Follow-ups", "mail.activity", "list", ACT_DOMAIN,
        {"group_by": ["activity_type_id"]}, "Follow-ups", ACT_VIEWS,
    )
    _list_block(act_cells, act_styles, 14, ids["list_act"], "Follow-ups", act_cells["A14"], [
        ("res_name", "Opportunity"), ("activity_type_id", "Type"), ("user_id", "Assigned To"),
        ("date_deadline", "Due"), ("summary", "Summary"),
    ], ["A", "B", "C", "D", "E"])
    act_cells["A30"] = _view_link(
        "By Type", "mail.activity", "pivot", ACT_DOMAIN,
        {"group_by": ["activity_type_id"], "pivot_row_groupby": ["activity_type_id"], "pivot_measures": ["__count"]},
        "Follow-ups", ACT_VIEWS,
    )
    act_cells["A31"] = "=PIVOT(%s,10,FALSE,FALSE)" % ids["act_type"]
    act_styles["A30:C30"] = 1
    act_cells["E30"] = _view_link(
        "By Salesperson", "mail.activity", "pivot", ACT_DOMAIN,
        {"group_by": ["user_id"], "pivot_row_groupby": ["user_id"], "pivot_measures": ["__count"]},
        "Follow-ups", ACT_VIEWS,
    )
    act_cells["E31"] = "=PIVOT(%s,10,FALSE,FALSE)" % ids["act_user"]
    act_styles["E30:G30"] = 1
    act_rows = _row_sizes({"14": {"size": 36}, "30": {"size": 36}})
    for row in range(15, 26):
        act_rows[str(row)] = {"size": 28}
    act_sheet = _blank_sheet("sheet_follow", "Follow-up", act_cells, act_figures, act_rows, _standard_cols(), 8, 50, act_styles)

    dashboard = next(sheet for sheet in data["sheets"] if sheet["name"] == "Dashboard")
    enquiry_card = _scorecard(
        "crm-enquiries-sales", "No. of Enquiries", "Data!D11", "Data!E11",
        895, 11, blue,
    )
    enquiry_card["width"] = 200
    dashboard["figures"].append(enquiry_card)
    sheets = []
    for sheet in data["sheets"]:
        sheets.append(sheet)
        if sheet["name"] == "Dashboard":
            sheets.extend([crm_sheet, won_sheet, lost_sheet, po_sheet, act_sheet])
    data["sheets"] = sheets

    refs = data.setdefault("chartOdooMenusReferences", {})
    refs["crm-enquiries-sales"] = "crm.menu_crm_opportunities"
    refs["crm-r1-0"] = "crm.menu_crm_opportunities"
    refs["crm-r1-1"] = "crm.crm_opportunity_report_menu"
    refs["crm-r1-2"] = "sale.menu_sale_quotations"
    refs["crm-r1-3"] = "sale.menu_sale_quotations"
    refs["crm-r1-4"] = "sale.menu_sale_quotations"
    refs["crm-r2-0"] = "crm.menu_crm_opportunities"
    refs["crm-r2-1"] = "crm.menu_crm_opportunities"
    refs["crm-r2-2"] = "crm.menu_crm_opportunities"
    refs["crm-r2-3"] = "sale.menu_sale_order"
    refs["crm-r2-4"] = "crm.crm_lead_menu_my_activities"
    refs["crm-r3-0"] = "crm.crm_opportunity_report_menu"
    refs["crm-r3-1"] = "crm.crm_opportunity_report_menu"
    refs["crm-r3-2"] = "crm.menu_crm_opportunities"
    refs["crm-r3-3"] = "crm.menu_crm_opportunities"
    refs["crm-r3-4"] = "crm.menu_crm_opportunities"
    refs["crm-monthly"] = "crm.crm_opportunity_report_menu"
    refs["crm-stages"] = "crm.menu_crm_opportunities"
    refs["won-0"] = "crm.menu_crm_opportunities"
    refs["won-1"] = "crm.crm_opportunity_report_menu"
    refs["won-user"] = "crm.crm_opportunity_report_menu"
    refs["won-month"] = "crm.crm_opportunity_report_menu"
    refs["lost-0"] = "crm.menu_crm_opportunities"
    refs["lost-1"] = "crm.crm_opportunity_report_menu"
    refs["lost-reason"] = "crm.crm_opportunity_report_menu"
    refs["lost-month"] = "crm.crm_opportunity_report_menu"
    refs["po-0"] = "sale.menu_sale_order"
    refs["po-1"] = "sale.menu_sale_order"
    refs["po-2"] = "sale.menu_sale_order"
    refs["po-month"] = "sale.menu_sale_report"
    refs["po-product"] = "sale.menu_sale_report"
    refs["act-0"] = "crm.crm_lead_menu_my_activities"
    refs["act-type"] = "crm.crm_activity_report_menu"
    refs["act-user"] = "crm.crm_activity_report_menu"

    data["revisionId"] = "AL_CRM_DASHBOARD_1"
    data["alCrmDashboard"] = 1
    return data

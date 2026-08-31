import frappe
from frappe import _


def execute(filters=None):
	filters = filters or {}
	columns = get_columns()

	rfq_name = filters.get("rfq")
	if not rfq_name:
		return columns, []

	return columns, get_data(rfq_name)


def get_columns():
	return [
		{"label": _("Rank"), "fieldname": "rank", "fieldtype": "Int", "width": 70},
		{"label": _("Supplier"), "fieldname": "supplier", "fieldtype": "Link", "options": "Supplier", "width": 200},
		{"label": _("Items Quoted"), "fieldname": "items_quoted", "fieldtype": "Int", "width": 110},
		{"label": _("Avg Price Score"), "fieldname": "average_price_score", "fieldtype": "Float", "precision": 2, "width": 130},
		{"label": _("Avg Lead Time Score"), "fieldname": "average_lead_time_score", "fieldtype": "Float", "precision": 2, "width": 150},
		{"label": _("Avg Weighted Mark"), "fieldname": "average_mark", "fieldtype": "Float", "precision": 2, "width": 140},
		{"label": _("Status"), "fieldname": "status", "fieldtype": "Data", "width": 240},
	]


def get_data(rfq_name):
	"""Same computation the portal's By Proposal view uses (proc_app.api.rfq.
	compute_by_proposal_ranking), fed the same shape of input -- grouped by
	item_code off the comparison sheet's own child rows, exactly matching
	proc_portal.api.rfqs.get_comparison_sheet()'s own construction so the two
	surfaces can never silently drift apart."""
	from proc_app.api.rfq import compute_by_proposal_ranking

	sheet_name = frappe.db.get_value("RFQ Comparison Sheet", {"request_for_quotation": rfq_name}, "name")
	if not sheet_name:
		return []

	doc = frappe.get_doc("RFQ Comparison Sheet", sheet_name)
	by_item = {}
	for row in doc.items:
		by_item.setdefault(row.item_code, []).append({
			"supplier": row.supplier,
			"price_score": row.price_score,
			"lead_time_score": row.lead_time_score,
			"weighted_mark": row.weighted_mark,
			"is_selected": row.is_selected,
		})

	total_item_count = len(by_item)
	all_rows = [row for rows in by_item.values() for row in rows]
	by_proposal = compute_by_proposal_ranking(all_rows, total_item_count)

	data = []
	for row in by_proposal:
		if row["eligible"]:
			status = _("Eligible")
		else:
			status = _("Incomplete — missing {0} of {1} items").format(row["items_missing"], total_item_count)
		data.append({
			"rank": row["rank"],
			"supplier": row["supplier"],
			"items_quoted": row["items_quoted"],
			"average_price_score": row["average_price_score"],
			"average_lead_time_score": row["average_lead_time_score"],
			"average_mark": row["average_mark"],
			"status": status,
		})
	return data

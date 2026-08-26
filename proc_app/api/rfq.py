import json

import frappe


def submit_quotation(rfq_name, supplier, items):
	"""Core supplier quotation submission logic. Caller is responsible for
	authorization (confirming the acting supplier is actually listed on this
	RFQ) — `supplier` must be passed explicitly here since a Request for
	Quotation can list multiple suppliers in its own `suppliers` child table,
	unlike Purchase Order/Purchase Invoice which each belong to exactly one
	supplier and can have it derived from the document itself."""
	if isinstance(items, str):
		items = json.loads(items)

	if not items or not isinstance(items, list):
		frappe.throw("At least one item is required.", frappe.ValidationError)

	for item in items:
		rate = float(item.get("rate") or 0)
		if rate <= 0:
			frappe.throw(
				f"Rate for item '{item.get('item_code', '')}' must be greater than zero.",
				frappe.ValidationError
			)

	# A supplier has no way to know or provide the buyer's internal warehouse,
	# but ERPNext requires one per stock item row on Supplier Quotation. Auto-fill
	# from the item's per-company default (same mechanism already proven in
	# proc_portal's New Request form) — invisible to the supplier, with a clear
	# error instead of ERPNext's raw validation message if no default exists.
	# Also used explicitly below as the new Supplier Quotation's own `company`
	# (not left to ERPNext's ambient default, which resolved to the wrong
	# company in live testing — same class of bug already fixed once before
	# in proc_portal's create_request()).
	company = frappe.db.get_value("Request for Quotation", rfq_name, "company")
	for item in items:
		if not item.get("warehouse"):
			default_warehouse = frappe.db.get_value(
				"Item Default", {"parent": item.get("item_code"), "company": company}, "default_warehouse"
			)
			if default_warehouse:
				item["warehouse"] = default_warehouse
			else:
				frappe.throw(
					f"Item {item.get('item_code')} has no default warehouse configured for {company}. "
					f"Please contact procurement to set one before this quotation can be submitted."
				)

	sq = frappe.get_doc({
		"doctype": "Supplier Quotation",
		"supplier": supplier,
		"company": company,
		"transaction_date": frappe.utils.today(),
		"items": []
	})

	for item in items:
		sq.append("items", {
			"item_code": item.get("item_code"),
			"qty": item.get("qty"),
			"rate": float(item.get("rate") or 0),
			"uom": item.get("uom"),
			"warehouse": item.get("warehouse"),
			"request_for_quotation": rfq_name,
			"request_for_quotation_item": item.get("name"),
			"lead_time_days": item.get("lead_time_days"),
			"expected_delivery_date": item.get("expected_delivery_date"),
		})

	sq.insert(ignore_permissions=True)
	# ERPNext's own quote_status sync (Request for Quotation Supplier ->
	# Received) only runs from Supplier Quotation's on_submit hook — leaving
	# this as a Draft would silently strand the RFQ's status tracking forever.
	# A supplier's quotation submission is final from their side, so submitting
	# here matches the real-world action, not just an editable draft.
	sq.submit()
	frappe.db.commit()
	return {"success": True, "quotation_name": sq.name}

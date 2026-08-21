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

	sq = frappe.get_doc({
		"doctype": "Supplier Quotation",
		"supplier": supplier,
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
			"request_for_quotation_item": item.get("name")
		})

	sq.insert(ignore_permissions=True)
	frappe.db.commit()
	return {"success": True, "quotation_name": sq.name}

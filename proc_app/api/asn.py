import json

import frappe


def submit_asn(po_name, expected_delivery_date, shipment_reference, notes, items):
	"""Core ASN submission logic. Caller is responsible for authorization
	(confirming the acting party owns/is entitled to submit against this PO)."""
	if isinstance(items, str):
		items = json.loads(items)

	if not items or not isinstance(items, list):
		frappe.throw("At least one item is required.", frappe.ValidationError)

	valid_items = [i for i in items if float(i.get("qty") or 0) > 0]
	if not valid_items:
		frappe.throw(
			"At least one item must have a quantity greater than zero.",
			frappe.ValidationError
		)

	asn = frappe.get_doc({
		"doctype": "Supplier ASN",
		"purchase_order": po_name,
		"supplier": frappe.db.get_value("Purchase Order", po_name, "supplier"),
		"expected_delivery_date": expected_delivery_date,
		"shipment_reference": shipment_reference or "",
		"notes": notes or "",
		"status": "Draft",
		"items": [],
	})

	for item in valid_items:
		asn.append("items", {
			"item_code": item.get("item_code"),
			"item_name": item.get("item_name"),
			"qty": float(item.get("qty")),
			"uom": item.get("uom"),
			"po_detail": item.get("name"),
		})

	asn.insert(ignore_permissions=True)
	frappe.db.commit()
	return {"success": True, "asn_name": asn.name}

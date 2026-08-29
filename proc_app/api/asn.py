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


@frappe.whitelist()
def make_purchase_receipt_from_asn(source_name, target_doc=None):
	"""Bridges Supplier ASN -> Purchase Receipt, since ERPNext's native mapper
	only maps from Purchase Order. Reuses that native mapper via its own
	filtered_children selection (same pattern already proven for Supplier
	Quotation -> Purchase Order), then corrects quantities afterward: the
	native mapper defaults each row's qty to ordered-minus-received (the
	PO's own outstanding total), not this specific ASN's shipped quantity —
	the two differ whenever a supplier ships in multiple partial ASNs."""
	from erpnext.buying.doctype.purchase_order.purchase_order import make_purchase_receipt

	asn = frappe.get_doc("Supplier ASN", source_name)
	po_name = asn.purchase_order

	po_items = frappe.get_all("Purchase Order Item", filters={"parent": po_name}, fields=["name", "item_code"])
	asn_item_map = {i.item_code: i.qty for i in asn.items}
	filtered_rows = [p.name for p in po_items if p.item_code in asn_item_map]

	pr = make_purchase_receipt(po_name, target_doc, args={"filtered_children": filtered_rows})

	for item in pr.items:
		if item.item_code in asn_item_map:
			asn_qty = asn_item_map[item.item_code]
			item.qty = asn_qty
			item.stock_qty = asn_qty * (item.conversion_factor or 1)
			item.amount = asn_qty * (item.rate or 0)
			item.base_amount = item.amount * (pr.conversion_rate or 1)

	return pr

import json

import frappe


def get_po_items_for_invoice(po_name):
	"""Core query: PO items with already-received (GRN) quantities, for building
	an invoice against a Purchase Order. No authorization performed here — caller
	must confirm the acting party is entitled to view/act on this PO."""
	po_items = frappe.get_list(
		"Purchase Order Item",
		filters={"parent": po_name},
		fields=["name", "item_code", "item_name", "uom", "qty", "rate"],
		order_by="idx asc",
		ignore_permissions=True
	)

	result = []
	for item in po_items:
		grn_qty = frappe.db.sql("""
			SELECT COALESCE(SUM(qty), 0)
			FROM `tabPurchase Receipt Item`
			WHERE purchase_order_item = %s AND docstatus = 1
		""", item.name)[0][0] or 0

		result.append({
			"item_code": item.item_code,
			"item_name": item.item_name or "",
			"uom": item.uom or "",
			"po_qty": float(item.qty or 0),
			"grn_qty": float(grn_qty),
			"rate": float(item.rate or 0),
			"po_detail": item.name
		})

	return result


def submit_invoice(po_name, bill_no, bill_date, due_date, notes, items):
	"""Core invoice submission logic. Caller is responsible for authorization
	(confirming the acting party owns/is entitled to submit against this PO)."""
	if isinstance(items, str):
		items = json.loads(items)

	if not items or not isinstance(items, list):
		frappe.throw("At least one item is required.", frappe.ValidationError)

	po = frappe.get_doc("Purchase Order", po_name, ignore_permissions=True)

	invoice_items = []
	for item in items:
		qty = float(item.get("qty") or 0)
		if not qty:
			continue
		rate = float(item.get("rate") or 0)
		if rate <= 0:
			frappe.throw(
				f"Rate for item '{item.get('item_code', '')}' must be greater than zero.",
				frappe.ValidationError
			)
		po_detail = item.get("po_detail")
		expense_account = frappe.db.get_value(
			"Purchase Order Item", po_detail, "expense_account"
		) if po_detail else None
		invoice_items.append({
			"item_code": item.get("item_code"),
			"qty": qty,
			"rate": rate,
			"uom": item.get("uom"),
			"purchase_order": po_name,
			"po_detail": po_detail,
			"expense_account": expense_account
		})

	if not invoice_items:
		frappe.throw(
			"At least one item with a quantity greater than zero is required.",
			frappe.ValidationError
		)

	invoice = frappe.get_doc({
		"doctype": "Purchase Invoice",
		"supplier": po.supplier,
		"company": po.company,
		"currency": po.currency,
		"buying_price_list": po.buying_price_list,
		"bill_no": bill_no.strip(),
		"bill_date": bill_date,
		"posting_date": bill_date,
		"due_date": due_date or bill_date,
		"remarks": notes or "",
		"items": invoice_items
	})

	invoice.set_missing_values()
	invoice.insert(ignore_permissions=True)
	frappe.db.commit()
	return {"success": True, "invoice_name": invoice.name}


def submit_dispute(invoice_name, dispute_type, description):
	"""Core dispute submission logic. Caller is responsible for authorization
	(confirming the acting party owns/is entitled to dispute this invoice)."""
	if len(description.strip()) <= 10:
		frappe.throw("Description must be more than 10 characters.", frappe.ValidationError)

	supplier = frappe.db.get_value("Purchase Invoice", invoice_name, "supplier")

	existing = frappe.db.get_value(
		"Supplier Invoice Dispute",
		{"purchase_invoice": invoice_name, "status": ["in", ["Open", "Under Review"]]},
		"name"
	)
	if existing:
		frappe.throw(
			"An open dispute already exists for this invoice: " + existing,
			frappe.ValidationError
		)

	dispute = frappe.get_doc({
		"doctype": "Supplier Invoice Dispute",
		"purchase_invoice": invoice_name,
		"supplier": supplier,
		"dispute_type": dispute_type,
		"description": description,
		"status": "Open"
	})
	dispute.insert(ignore_permissions=True)
	frappe.db.commit()
	return {"success": True, "dispute_name": dispute.name}

import frappe


def acknowledge_po(po_name, note=None):
	"""Core PO acknowledgment logic. Caller is responsible for authorization
	(confirming the acting party is entitled to acknowledge this specific PO) —
	this function only enforces the domain rule (can't acknowledge twice).

	Uses a raw frappe.db.set_value() rather than the Document API (doc.save())
	deliberately: these 3 custom fields have allow_on_submit=0, and a Purchase
	Order is always docstatus=1 (submitted) by the time it's being acknowledged —
	doc.save() would be rejected by Frappe's own submit-state field validation.
	This matches the original supplier_portal implementation's mechanism exactly."""
	po = frappe.get_doc("Purchase Order", po_name)
	if po.supplier_acknowledged:
		frappe.throw("This order has already been acknowledged.")
	frappe.db.set_value("Purchase Order", po_name, {
		"supplier_acknowledged": 1,
		"supplier_acknowledged_on": frappe.utils.now(),
		"supplier_acknowledgment_note": note or "",
	})
	frappe.db.commit()
	return {"success": True, "message": "Order acknowledged successfully."}


def request_amendment(po_name, reason):
	"""Core amendment-request logic via Comment doctype — no dedicated
	Purchase Order Amendment doctype exists in ERPNext (confirmed earlier
	in this project's OOB-vs-Custom audit)."""
	comment = frappe.get_doc({
		"doctype": "Comment",
		"comment_type": "Comment",
		"reference_doctype": "Purchase Order",
		"reference_name": po_name,
		"content": f"<b>Amendment Request from Supplier Portal:</b><br>{reason}",
		"comment_by": frappe.session.user,
	})
	comment.insert(ignore_permissions=True)
	frappe.db.commit()
	return {"success": True, "message": "Amendment request submitted."}

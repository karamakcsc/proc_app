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


def request_amendment(po_name, amendment_type, reason):
	"""Core amendment-request logic — creates a real Purchase Order Amendment
	instead of the plain Comment this used to post (retired: that mechanism
	predates the Purchase Order Amendment doctype existing in this project).

	Does NOT use apply_workflow(doc, "Submit") the way proc_portal's own
	internal create_amendment() does — the "Purchase Order Amendment Approval"
	workflow's Draft->Pending Approval "Submit" transition is gated to the
	Procurement Officer role (confirmed via the real Workflow Transition rows),
	and a supplier portal session never holds that role. Sets workflow_state
	directly via db_set instead, bypassing transition-graph validation — the
	same deliberate, already-proven pattern used in material_request_hooks.py's
	spawn hook, since this is a system-driven continuation on the supplier's
	behalf, not a genuine internal-staff workflow transition."""
	doc = frappe.get_doc({
		"doctype": "Purchase Order Amendment",
		"purchase_order": po_name,
		"amendment_type": amendment_type,
		"description": reason,
		"reason": reason,
		"requested_by": frappe.session.user,
	})
	doc.insert(ignore_permissions=True)
	doc.db_set("workflow_state", "Pending Approval", update_modified=False)
	frappe.db.commit()
	return {"success": True, "name": doc.name}

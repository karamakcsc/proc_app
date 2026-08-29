import frappe

def on_material_request_update(doc, method):
	"""Spawns a linked Purchase-type Material Request when the original transitions
	to 'Forwarded to Purchase', and stops the original via ERPNext's native mechanism."""

	if doc.workflow_state != "Forwarded to Purchase":
		return

	before = doc.get_doc_before_save()
	if before and before.get("workflow_state") == "Forwarded to Purchase":
		return  # not a fresh transition, avoid re-triggering on every subsequent save

	if frappe.db.exists("Material Request", {"source_material_request": doc.name}):
		return  # safety net against duplicate spawning

	company = frappe.db.get_value("Department", doc.requesting_department, "company")
	if not company:
		frappe.throw(f"Could not determine company for department {doc.requesting_department}")

	new_doc = frappe.get_doc({
		"doctype": "Material Request",
		"material_request_type": "Purchase",
		"company": company,
		"transaction_date": frappe.utils.today(),
		"schedule_date": doc.schedule_date,
		"requesting_department": doc.requesting_department,
		"concerned_department": doc.concerned_department,
		"source_material_request": doc.name,
		"items": [
			{
				"item_code": item.item_code,
				"qty": item.qty,
				"schedule_date": item.schedule_date,
				"warehouse": item.warehouse,
			}
			for item in doc.items
		],
	})
	new_doc.insert(ignore_permissions=True)

	# Carry over any supporting documents attached to the original request — without
	# this, Forward-to-Purchase would silently drop them, since the spawned document
	# is a brand-new record with no attachments of its own. Reuses Frappe's own native
	# File.create_attachment_copy() (frappe/core/doctype/file/file.py) rather than
	# hand-building File records, since it correctly reuses file_url (no duplicate
	# file content), respects attachment limits, and logs the copy as a Comment.
	original_attachments = frappe.get_all(
		"File",
		filters={"attached_to_doctype": doc.doctype, "attached_to_name": doc.name},
		pluck="name",
	)
	for file_name in original_attachments:
		frappe.get_doc("File", file_name).create_attachment_copy(
			new_doc.doctype, new_doc.name, ignore_permissions=True
		)

	# Set workflow_state directly via db_set (bypasses transition-graph validation,
	# deliberate here since this is a system-driven continuation, not a user transition)
	new_doc.db_set("workflow_state", "Pending Concerned-Dept Manager Approval", update_modified=False)

	frappe.logger().info(f"proc_app: spawned linked Purchase Material Request {new_doc.name} from {doc.name}")

	# Stop the original using ERPNext's own native mechanism (confirmed reliable via
	# earlier audit) — act on the same doc object already mid-save, not a fresh fetch
	doc.update_status("Stopped")

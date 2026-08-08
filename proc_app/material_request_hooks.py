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

	new_doc = frappe.get_doc({
		"doctype": "Material Request",
		"material_request_type": "Purchase",
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
	# Set workflow_state directly via db_set (bypasses transition-graph validation,
	# deliberate here since this is a system-driven continuation, not a user transition)
	new_doc.db_set("workflow_state", "Pending Concerned-Dept Manager Approval", update_modified=False)

	frappe.logger().info(f"proc_app: spawned linked Purchase Material Request {new_doc.name} from {doc.name}")

	# Stop the original using ERPNext's own native mechanism (confirmed reliable via
	# earlier audit) — act on the same doc object already mid-save, not a fresh fetch
	doc.update_status("Stopped")

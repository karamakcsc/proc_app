import frappe

MILESTONE_DAYS = [30, 14, 7, 1]

def check_contract_expiry():
	"""Daily scheduled check: notifies Procurement Officers when an Active
	contract is exactly 30, 14, 7, or 1 day(s) from its end_date — milestone-based
	so people aren't re-notified every single day once a contract enters the
	warning window, only at these specific checkpoints."""
	today = frappe.utils.today()
	contracts = frappe.get_all(
		"Contract",
		filters={"status": "Active", "end_date": ["is", "set"]},
		fields=["name", "party_name", "party_type", "end_date"],
	)

	procurement_officers = frappe.get_all(
		"Has Role", filters={"role": "Procurement Officer", "parenttype": "User"}, pluck="parent"
	)
	if not procurement_officers:
		return

	for c in contracts:
		days_remaining = frappe.utils.date_diff(c.end_date, today)
		if days_remaining in MILESTONE_DAYS:
			for user in procurement_officers:
				frappe.get_doc({
					"doctype": "Notification Log",
					"for_user": user,
					"type": "Alert",
					"subject": f"Contract {c.name} ({c.party_name}) expires in {days_remaining} day(s) — {c.end_date}",
					"document_type": "Contract",
					"document_name": c.name,
				}).insert(ignore_permissions=True)
	frappe.db.commit()

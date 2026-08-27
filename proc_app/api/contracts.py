import frappe

def check_contract_expiry():
	"""Daily scheduled check: notifies Procurement Officers every day once a
	contract is within 7 days of its end_date, through the expiry day itself
	(0 days remaining) — a persistent daily reminder, not a one-time milestone,
	per Yasser's decision (2026-08-27). Once a contract's end_date passes,
	Contract's own native status logic flips it to Inactive, which naturally
	excludes it from this check going forward — no extra bound needed.
	Includes a same-day duplicate guard so re-running this job (manual trigger,
	scheduler retry, etc.) doesn't spam the same person twice in one day."""
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
		if 0 <= days_remaining <= 7:
			for user in procurement_officers:
				already_sent_today = frappe.db.exists(
					"Notification Log",
					{
						"for_user": user,
						"document_type": "Contract",
						"document_name": c.name,
						"creation": [">=", today],
					},
				)
				if already_sent_today:
					continue
				frappe.get_doc({
					"doctype": "Notification Log",
					"for_user": user,
					"type": "Alert",
					"subject": f"Contract {c.name} ({c.party_name}) expires in {days_remaining} day(s) — {c.end_date}",
					"document_type": "Contract",
					"document_name": c.name,
				}).insert(ignore_permissions=True)
	frappe.db.commit()

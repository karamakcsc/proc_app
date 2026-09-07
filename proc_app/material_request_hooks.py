import frappe

def validate_department_company(doc, method):
	"""Cross-company department guard for the desk (and any other API path that
	doesn't go through proc_portal's create_request(), which has its own copy of
	this same check for concerned_department -- requesting_department can't
	mismatch there, company is derived from it directly; here, in the desk, either
	field can be set to any department regardless of company, so both are checked).
	This is the real fix for a live bug: a Material Request created with
	company="KCSC (Demo)" but requesting_department="Accounts - K" (a KCSC
	department) later broke the Forward-to-Purchase spawn -- material_request_hooks.py's
	on_material_request_update() now correctly copies company from the source
	document rather than re-deriving it from the department, but that only stops
	an already-mismatched request from corrupting its spawn further. Rejecting the
	mismatch here, at creation/save, stops it from ever existing in the first
	place. A blank Department.company is treated as "any company" -- confirmed
	live that only the root "All Departments" group node has one, never a real,
	selectable leaf department."""
	for fieldname, label in (
		("requesting_department", "Requesting Department"),
		("concerned_department", "Concerned Department"),
	):
		department = doc.get(fieldname)
		if not department:
			continue
		dept_company = frappe.db.get_value("Department", department, "company")
		if dept_company and dept_company != doc.company:
			frappe.throw(
				f"{label} '{department}' belongs to company '{dept_company}', but this request is for "
				f"'{doc.company}'. Please select a department from the correct company."
			)

def propagate_cost_center(doc, method):
	"""Server-side counterpart to the desk 'Cost Center' (set_cost_center) header
	field's Client Script (Material Request Set Cost Center) -- Yasser's explicit
	choice (superseding the earlier fill-blanks-only decision, PROC_APP_SPEC.md
	v1.78): overwrite every item row when set_cost_center genuinely CHANGES,
	mirroring ERPNext's own autofill_warehouse() (erpnext/public/js/controllers/
	transaction.js) -- but do NOT re-apply on every save, so a per-row edit made
	afterwards survives a later save where the header field itself didn't change.
	Runs on before_validate (before the item rows are persisted), so a document
	built via desk, the portal, or any other API path all behave identically --
	the Client Script only covers the desk form.

	"Changed" is determined by comparing against get_doc_before_save() rather than
	just "is set_cost_center truthy", which would reapply on every single save
	exactly like the old fill-blanks behavior did. get_doc_before_save() returns
	None for a brand-new document (confirmed via frappe/model/document.py's
	load_doc_before_save(): it returns immediately, before populating
	_doc_before_save, when self.is_new() is true) -- treated here as "changed",
	since a new document setting set_cost_center has no prior state to compare
	against and should apply to every row, matching the Client Script's own
	behavior for a freshly-filled-in form."""
	if not doc.get("set_cost_center"):
		return
	before = doc.get_doc_before_save()
	changed = before is None or before.get("set_cost_center") != doc.set_cost_center
	if not changed:
		return
	for item in doc.items:
		item.cost_center = doc.set_cost_center

def on_material_request_update(doc, method):
	"""Spawns a linked Purchase-type Material Request when the original transitions
	to 'Forwarded to Purchase', and stops the original via ERPNext's native mechanism.
	cost_center is carried across item-by-item -- same "would silently drop it"
	risk class as the attachment-copy step below, and the more consequential one:
	the original's own Material Issue type never triggers budget validation at
	all (Material Request.on_submit() only calls validate_budget() for type
	"Purchase"), so this spawn is the FIRST point in the whole chain where a
	portal requester's chosen cost center can actually reach a document that
	gets budget-checked on submit (PROC_PORTAL_SPEC.md's cost-center-on-New-Request
	entry)."""

	if doc.workflow_state != "Forwarded to Purchase":
		return

	before = doc.get_doc_before_save()
	if before and before.get("workflow_state") == "Forwarded to Purchase":
		return  # not a fresh transition, avoid re-triggering on every subsequent save

	if frappe.db.exists("Material Request", {"source_material_request": doc.name}):
		return  # safety net against duplicate spawning

	# Copy company from the source document -- do NOT re-derive it from
	# requesting_department. The v1.36 fix that introduced deriving from the
	# department was solving a different, real problem: new_doc never set
	# company at all, so it silently fell back to ERPNext's own ambient/session
	# default. Deriving from the department was one way to plug that gap, but
	# it re-introduced the same class of bug the moment a document's own
	# requesting_department belongs to a DIFFERENT company than the document
	# itself (a real case found live: a KCSC (Demo) request with a KCSC
	# requesting_department spawned a Purchase-type doc with company=KCSC,
	# while its copied item rows still carried KCSC (Demo) cost centers,
	# throwing AccountsController.validate_company()'s "Cost Center ... does
	# not belong to the Company" the instant it tried to save). doc.company is
	# mandatory on this doctype (reqd=1) and this hook only ever runs on an
	# already-validated, already-saved source document (on_update fires
	# post-save) -- it cannot genuinely be empty here, so a copy is always
	# correct and a "derive if empty" fallback would guard against a case that
	# cannot occur. Do not "helpfully" revert this back to a department
	# lookup -- see proc_portal's create_request()/before_validate department
	# validation (PROC_APP_SPEC.md / PROC_PORTAL_SPEC.md) for the real fix to
	# v1.36's underlying scenario: reject a mismatched department at creation,
	# not paper over it here.
	company = doc.company
	if not company:
		frappe.throw(f"Material Request {doc.name} has no company set — cannot spawn a linked Purchase request.")

	# Built as an explicit loop, not a list comprehension, so item_rows and
	# source_rates are provably in the same order by construction -- if a
	# filter is ever added here (only forwarding some rows), both lists would
	# stay in sync automatically, unlike a separate zip(doc.items, item_rows)
	# done after the fact, which could silently mispair the moment one list
	# gets filtered and the other doesn't. Not needed for correctness today
	# (this loop is currently unconditional, forwarding every row), but this
	# structure is what makes that a checkable fact rather than an assumption.
	item_rows = []
	source_rates = []
	for item in doc.items:
		item_rows.append(
			{
				"item_code": item.item_code,
				"qty": item.qty,
				"rate": item.rate,
				"schedule_date": item.schedule_date,
				"warehouse": item.warehouse,
				"cost_center": item.cost_center,
			}
		)
		source_rates.append({"item_code": item.item_code, "qty": item.qty, "rate": item.rate})

	new_doc = frappe.get_doc({
		"doctype": "Material Request",
		"material_request_type": "Purchase",
		"company": company,
		"transaction_date": frappe.utils.today(),
		"schedule_date": doc.schedule_date,
		"requesting_department": doc.requesting_department,
		"concerned_department": doc.concerned_department,
		"source_material_request": doc.name,
		"items": item_rows,
	})
	new_doc.insert(ignore_permissions=True)

	# Same root cause and same fix as proc_portal.api.requests.create_request()
	# (PROC_PORTAL_SPEC.md v2.17): MaterialRequest.on_update() unconditionally
	# re-derives every row's rate from the default Buying Price List on a
	# brand-new insert (has_value_changed("buying_price_list") always returns
	# True pre-insert), silently discarding the rate just copied above.
	# Reapplied here via db_set(), the same mechanism update_item_rates()
	# itself uses, not a second validate()/save() cycle.
	for db_item, source in zip(new_doc.items, source_rates):
		db_item.db_set(
			{
				"rate": source["rate"],
				"amount": frappe.utils.flt(source["rate"] * source["qty"], db_item.precision("amount")),
			},
			update_modified=False,
		)

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

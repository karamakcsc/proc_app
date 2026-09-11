import frappe
from frappe.permissions import add_permission, update_permission_property

DOCTYPE = "Material Request"

# (role, read, write, create, submit)
ROLE_PERMS = [
	("Department User",     1, 1, 1, 0),
	("Department Manager",  1, 1, 0, 0),
	("Department Officer",  1, 1, 0, 1),
	("Procurement Officer", 1, 1, 0, 1),
]

SUPPORTING_DOCTYPES = ["Item", "Item Group", "UOM", "Warehouse", "Brand", "Company", "Department", "Price List"]
SUPPORTING_ROLES = ["Department User", "Department Manager", "Department Officer", "Procurement Officer"]


def after_migrate():
	setup_material_request_permissions()
	setup_supporting_doctype_permissions()
	setup_po_amendment_permissions()
	setup_stock_settings_permission()
	setup_rfq_permissions()
	setup_report_permissions()
	setup_comparison_sheet_permissions()
	setup_po_generation_permissions()
	setup_contract_permissions()
	setup_asn_grn_permissions()
	setup_master_data_permissions()


def setup_material_request_permissions():
	if not frappe.db.exists("DocType", DOCTYPE):
		frappe.logger().warning(
			f"setup_material_request_permissions: DocType '{DOCTYPE}' not found, skipping"
		)
		return

	for role, read, write, create, submit in ROLE_PERMS:
		if not frappe.db.exists("Role", role):
			frappe.logger().warning(
				f"setup_material_request_permissions: Role '{role}' not found, skipping"
			)
			continue

		# Remove any existing Custom DocPerm for this role to avoid duplicates on re-run
		frappe.db.delete("Custom DocPerm", {"parent": DOCTYPE, "role": role, "permlevel": 0})

		add_permission(DOCTYPE, role, permlevel=0)
		for ptype, value in [
			("read", read),
			("write", write),
			("create", create),
			("submit", submit),
		]:
			update_permission_property(DOCTYPE, role, 0, ptype, value)

	frappe.db.commit()
	frappe.clear_cache()
	frappe.logger().info("KCSC Proc: Material Request DocPerm records configured for 4 roles.")


def setup_supporting_doctype_permissions():
	for doctype in SUPPORTING_DOCTYPES:
		if not frappe.db.exists("DocType", doctype):
			frappe.logger().warning(
				f"setup_supporting_doctype_permissions: DocType '{doctype}' not found, skipping"
			)
			continue

		for role in SUPPORTING_ROLES:
			if not frappe.db.exists("Role", role):
				frappe.logger().warning(
					f"setup_supporting_doctype_permissions: Role '{role}' not found, skipping"
				)
				continue

			# Remove any existing Custom DocPerm for this role to avoid duplicates on re-run
			frappe.db.delete("Custom DocPerm", {"parent": doctype, "role": role, "permlevel": 0})

			add_permission(doctype, role, permlevel=0)
			for ptype, value in [
				("read", 1),
				("write", 0),
				("create", 0),
				("submit", 0),
			]:
				update_permission_property(doctype, role, 0, ptype, value)

	frappe.db.commit()
	frappe.clear_cache()
	frappe.logger().info(
		"KCSC Proc: read-only DocPerm records configured on 5 supporting doctypes for 4 roles."
	)


def setup_po_amendment_permissions():
	doctype = "Purchase Order Amendment"
	role = "Procurement Officer"

	if not frappe.db.exists("DocType", doctype):
		frappe.logger().warning(
			f"setup_po_amendment_permissions: DocType '{doctype}' not found, skipping"
		)
		return

	if not frappe.db.exists("Role", role):
		frappe.logger().warning(
			f"setup_po_amendment_permissions: Role '{role}' not found, skipping"
		)
		return

	# Remove any existing Custom DocPerm for this role to avoid duplicates on re-run
	frappe.db.delete("Custom DocPerm", {"parent": doctype, "role": role, "permlevel": 0})

	add_permission(doctype, role, permlevel=0)
	for ptype, value in [
		("read", 1),
		("write", 1),
		("create", 1),
		("submit", 1),
	]:
		update_permission_property(doctype, role, 0, ptype, value)

	# Procurement Officer also needs read access to Purchase Order itself,
	# to select it on the PO Amendment form's link field.
	if not frappe.db.exists("Custom DocPerm", {"parent": "Purchase Order", "role": "Procurement Officer"}):
		add_permission("Purchase Order", "Procurement Officer", 0)
		update_permission_property("Purchase Order", "Procurement Officer", 0, "read", 1)

	frappe.db.commit()
	frappe.clear_cache()
	frappe.logger().info("KCSC Proc: Purchase Order Amendment DocPerm configured for Procurement Officer.")


def setup_stock_settings_permission():
	doctype = "Stock Settings"
	role = "Department Officer"

	if not frappe.db.exists("DocType", doctype):
		frappe.logger().warning(
			f"setup_stock_settings_permission: DocType '{doctype}' not found, skipping"
		)
		return

	if not frappe.db.exists("Role", role):
		frappe.logger().warning(
			f"setup_stock_settings_permission: Role '{role}' not found, skipping"
		)
		return

	# Remove any existing Custom DocPerm for this role to avoid duplicates on re-run
	frappe.db.delete("Custom DocPerm", {"parent": doctype, "role": role, "permlevel": 0})

	add_permission(doctype, role, permlevel=0)
	update_permission_property(doctype, role, 0, "read", 1)

	frappe.db.commit()
	frappe.clear_cache()
	frappe.logger().info("KCSC Proc: Stock Settings read permission configured for Department Officer.")


def setup_rfq_permissions():
	doctype = "Request for Quotation"
	role = "Procurement Officer"

	if not frappe.db.exists("DocType", doctype):
		frappe.logger().warning(
			f"setup_rfq_permissions: DocType '{doctype}' not found, skipping"
		)
		return

	if not frappe.db.exists("Role", role):
		frappe.logger().warning(
			f"setup_rfq_permissions: Role '{role}' not found, skipping"
		)
		return

	# Remove any existing Custom DocPerm for this role to avoid duplicates on re-run
	frappe.db.delete("Custom DocPerm", {"parent": doctype, "role": role, "permlevel": 0})

	add_permission(doctype, role, permlevel=0)
	for ptype, value in [
		("read", 1),
		("write", 1),
		("create", 1),
		("submit", 1),
	]:
		update_permission_property(doctype, role, 0, ptype, value)

	# Procurement Officer also needs read access to Supplier itself,
	# to select suppliers on the RFQ form's suppliers child table.
	if not frappe.db.exists("Custom DocPerm", {"parent": "Supplier", "role": "Procurement Officer"}):
		add_permission("Supplier", "Procurement Officer", 0)
		update_permission_property("Supplier", "Procurement Officer", 0, "read", 1)

	frappe.db.commit()
	frappe.clear_cache()
	frappe.logger().info("KCSC Proc: Request for Quotation DocPerm configured for Procurement Officer.")


def setup_report_permissions():
	"""Query Reports check frappe.has_permission(ref_doctype, "report") — a distinct
	permission type from read/write/create/submit, confirmed via frappe/desk/query_report.py.
	Procurement Officer already has read=1 on Material Request but not report=1,
	so "Purchase Requisition Status" would otherwise raise a PermissionError on run,
	despite the role genuinely being able to read the underlying doctype. Same gap
	applies to "Items Below Reorder Level" (ref_doctype Item) for Department Officer
	and Procurement Officer — both already have read=1 on Item via SUPPORTING_DOCTYPES,
	just not report=1. Same gap again for "RFQ Comparison - By Proposal" (ref_doctype
	Request for Quotation): Procurement Officer already has read=1 via
	setup_rfq_permissions(), just not report=1."""
	grants = [
		("Material Request", "Procurement Officer"),
		("Item", "Department Officer"),
		("Item", "Procurement Officer"),
		("Request for Quotation", "Procurement Officer"),
	]

	# Budget, for "Budget Utilisation": unlike the grants above, Procurement
	# Officer has NO existing permission here at all (confirmed via a fresh
	# Custom DocPerm/DocPerm query -- same gap class as Stock Reconciliation
	# below), so both read and report must be granted together.
	doctype, role = "Budget", "Procurement Officer"
	if frappe.db.exists("DocType", doctype) and frappe.db.exists("Role", role):
		if not frappe.db.exists("Custom DocPerm", {"parent": doctype, "role": role}):
			add_permission(doctype, role, permlevel=0)
		update_permission_property(doctype, role, 0, "read", 1)
		update_permission_property(doctype, role, 0, "report", 1)

	for doctype, role in grants:
		if not frappe.db.exists("DocType", doctype):
			frappe.logger().warning(
				f"setup_report_permissions: DocType '{doctype}' not found, skipping"
			)
			continue

		if not frappe.db.exists("Role", role):
			frappe.logger().warning(
				f"setup_report_permissions: Role '{role}' not found, skipping"
			)
			continue

		update_permission_property(doctype, role, 0, "report", 1)

	# Stock Reconciliation, for "Physical Count Variance": unlike the grants above,
	# Department Officer has NO existing permission here at all (confirmed via a
	# fresh Custom DocPerm/DocPerm query — not even the native Stock User role has
	# read=1 on this doctype), so both read and report must be granted together,
	# not just report on top of an assumed-existing read.
	doctype, role = "Stock Reconciliation", "Department Officer"
	if frappe.db.exists("DocType", doctype) and frappe.db.exists("Role", role):
		if not frappe.db.exists("Custom DocPerm", {"parent": doctype, "role": role}):
			add_permission(doctype, role, permlevel=0)
		update_permission_property(doctype, role, 0, "read", 1)
		update_permission_property(doctype, role, 0, "report", 1)

	frappe.db.commit()
	frappe.clear_cache()
	frappe.logger().info("KCSC Proc: 'report' permission configured for Material Request/Item/Stock Reconciliation.")


def setup_comparison_sheet_permissions():
	"""RFQ Comparison Sheet was created (Stage C) with only System Manager
	permissions on the doctype itself — Procurement Officer, who actually
	generates and views these from proc_portal, had zero access. Child table
	rows (RFQ Comparison Sheet Item) don't need separate permissions, same
	rule already confirmed for every other child table in this project.

	Extended when the "Comparison Sheet Approval" workflow was added: the
	workflow's own role-based transition gate gets a supplier/officer session
	past the Approve *transition*, but Frappe separately enforces the
	doctype-level `submit` permission the instant apply_workflow() has to
	call doc.submit() itself (Approved's doc_status is 1, i.e. submitted) —
	the same two-layer gap already documented for Purchase Order Amendment
	and Purchase Invoice in this project. Found live, not assumed: a real
	Procurement Officer session got a genuine PermissionError on Approve
	before this was added."""
	doctype = "RFQ Comparison Sheet"
	role = "Procurement Officer"

	if not frappe.db.exists("DocType", doctype):
		frappe.logger().warning(
			f"setup_comparison_sheet_permissions: DocType '{doctype}' not found, skipping"
		)
		return

	if not frappe.db.exists("Role", role):
		frappe.logger().warning(
			f"setup_comparison_sheet_permissions: Role '{role}' not found, skipping"
		)
		return

	frappe.db.delete("Custom DocPerm", {"parent": doctype, "role": role, "permlevel": 0})

	add_permission(doctype, role, permlevel=0)
	for ptype, value in [
		("read", 1),
		("write", 1),
		("create", 1),
		("submit", 1),
	]:
		update_permission_property(doctype, role, 0, ptype, value)

	frappe.db.commit()
	frappe.clear_cache()
	frappe.logger().info("KCSC Proc: RFQ Comparison Sheet DocPerm configured for Procurement Officer.")


def setup_po_generation_permissions():
	"""PO-from-Comparison-Sheet Stage B: Procurement Officer already had read-only
	access to Purchase Order (granted in setup_po_amendment_permissions(), only to
	select a PO on the Amendment form's link field) but never create/write/submit —
	confirmed via a live PermissionError while testing generate_purchase_orders_from_comparison(),
	not assumed. Needed now to actually generate, review, and submit POs from a
	winning RFQ Comparison Sheet. Also grants read on Supplier Quotation itself:
	get_mapped_doc() checks read permission on the SOURCE document being mapped
	FROM, and Procurement Officer had zero access to Supplier Quotation at all
	(confirmed via a second live PermissionError, and via DocPerm/Custom DocPerm
	queries showing no native role or prior grant covered it). Also grants read
	on Account: ERPNext's own AccountsController.set_payment_schedule() (run
	during Purchase Order validate(), which ignore_permissions=True on insert()
	does NOT bypass, since it's an inline frappe.throw(exc=PermissionError) in
	business logic, not the doc-level insert check) resolves the supplier's
	party account and explicitly checks read access on it — the same class of
	gap already found and fixed once before for a different role
	(PROC_APP_SPEC.md Changelog v1.4, Account/Item for Supplier Portal User),
	confirmed via a third live PermissionError, not assumed. Also grants
	write/create/submit on Supplier Quotation itself (previously read-only,
	from the grant above): staff entering a quotation directly through the
	desk on a supplier's behalf, found via Yasser's hands-on testing, is a
	genuinely new use case — every prior quotation went through
	supplier_portal's own permission-bypassing insert(ignore_permissions=True),
	so this path had never actually been exercised under real permissions
	before."""
	doctype = "Purchase Order"
	role = "Procurement Officer"

	if not frappe.db.exists("DocType", doctype):
		frappe.logger().warning(
			f"setup_po_generation_permissions: DocType '{doctype}' not found, skipping"
		)
		return

	if not frappe.db.exists("Role", role):
		frappe.logger().warning(
			f"setup_po_generation_permissions: Role '{role}' not found, skipping"
		)
		return

	frappe.db.delete("Custom DocPerm", {"parent": doctype, "role": role, "permlevel": 0})

	add_permission(doctype, role, permlevel=0)
	for ptype, value in [
		("read", 1),
		("write", 1),
		("create", 1),
		("submit", 1),
	]:
		update_permission_property(doctype, role, 0, ptype, value)

	frappe.db.delete("Custom DocPerm", {"parent": "Supplier Quotation", "role": role, "permlevel": 0})
	add_permission("Supplier Quotation", role, permlevel=0)
	for ptype, value in [
		("read", 1),
		("write", 1),
		("create", 1),
		("submit", 1),
	]:
		update_permission_property("Supplier Quotation", role, 0, ptype, value)

	if not frappe.db.exists("Custom DocPerm", {"parent": "Account", "role": role, "permlevel": 0}):
		add_permission("Account", role, 0)
		update_permission_property("Account", role, 0, "read", 1)

	frappe.db.commit()
	frappe.clear_cache()
	frappe.logger().info("KCSC Proc: Purchase Order create/write/submit + Supplier Quotation/Account read configured for Procurement Officer.")


def setup_contract_permissions():
	"""Contract Management (Changelog v1.38) added a reverse link and expiry
	reminders but never granted Procurement Officer any access to Contract
	itself — a proactive check before Yasser's hands-on testing, same class
	of gap already found (and always this same way) for every other doctype
	touched by this project. Confirmed via DocPerm/Custom DocPerm queries:
	only Sales Manager/HR Manager/System Manager/Purchase Manager (all native,
	none of them this project's roles) have any access; Procurement Officer
	had zero. Also grants read on Contract Template: Contract's own form has
	a Link field to it (contract_template), and Yasser's hands-on testing hit
	"Insufficient Permission for Contract Template" — the same class of gap
	already documented for Account in setup_po_generation_permissions()
	(a linked doctype needs its own explicit read grant, insert()'s
	ignore_permissions doesn't cover Link-field reads triggered from the form).
	Also grants read+write on Purchase Invoice: full Contract linking
	(proc_portal Purchase Invoice Detail + reverse-lookup on Contract Detail)
	needs Procurement Officer to view PIs and set their `contract` link field
	from the portal. Originally granted read-only, reasoning "write/create not
	needed for viewing" — corrected after a live test caught the actual
	contradiction: the very feature this permission exists for (linking a PI
	to a Contract from the portal) is itself a write to the PI's `contract`
	field, which `set_contract_link()`'s own permission check (added after
	finding raw `db.set_value()` bypassed authorization entirely) correctly
	rejected without it. `create` WAS deliberately ungranted too, on the
	original grounds that "Purchase Invoices still originate only from the
	supplier submission flow already built, never manual portal creation" —
	reversed per direct instruction when a New Purchase Invoice form was
	commissioned for proc_portal (mirroring New Purchase Order), confirmed
	explicitly since it overrides that earlier architectural decision rather
	than silently patching around it. Found live: `doc.insert()` from the new
	form's `create_purchase_invoice()` genuinely raised `PermissionError`
	first, confirming the gap was real, not assumed. `submit` was ALSO
	deliberately ungranted at that point, on the grounds that invoices are
	built and reviewed via the portal's own unsaved-preview flow, then
	submitted through the normal desk/native process — reversed in turn once
	Purchase Invoice Detail itself needed a real Submit button (mirroring
	Purchase Order Detail's own established pattern), the same class of
	explicit, confirmed reversal as `create` above, not a silent expansion."""
	doctype = "Contract"
	role = "Procurement Officer"

	if not frappe.db.exists("DocType", doctype):
		frappe.logger().warning(
			f"setup_contract_permissions: DocType '{doctype}' not found, skipping"
		)
		return

	if not frappe.db.exists("Role", role):
		frappe.logger().warning(
			f"setup_contract_permissions: Role '{role}' not found, skipping"
		)
		return

	frappe.db.delete("Custom DocPerm", {"parent": doctype, "role": role, "permlevel": 0})

	add_permission(doctype, role, permlevel=0)
	for ptype, value in [
		("read", 1),
		("write", 1),
		("create", 1),
		("submit", 1),
	]:
		update_permission_property(doctype, role, 0, ptype, value)

	if not frappe.db.exists("Custom DocPerm", {"parent": "Contract Template", "role": role, "permlevel": 0}):
		add_permission("Contract Template", role, 0)
		update_permission_property("Contract Template", role, 0, "read", 1)

	frappe.db.delete("Custom DocPerm", {"parent": "Purchase Invoice", "role": role, "permlevel": 0})
	add_permission("Purchase Invoice", role, permlevel=0)
	for ptype, value in [
		("read", 1),
		("write", 1),
		("create", 1),
		("submit", 1),
	]:
		update_permission_property("Purchase Invoice", role, 0, ptype, value)

	frappe.db.commit()
	frappe.clear_cache()
	frappe.logger().info("KCSC Proc: Contract read/write/create/submit + Contract Template read configured for Procurement Officer.")


def setup_asn_grn_permissions():
	"""proc_portal's new ASN/Goods Receipt (Purchase Receipt) list/detail screens
	need Procurement Officer to read both doctypes — a proactive check before
	building those screens found zero existing Custom DocPerm rows for either,
	same recurring gap class as every other doctype touched by this project.
	Read-only originally: that was a viewing-only feature, no create/write/submit
	flow for either doctype from the portal side.

	Extended later to grant `create` on Purchase Receipt specifically: the new
	"Create > Purchase Receipt" desk button on Supplier ASN (make_purchase_receipt_from_asn())
	reuses ERPNext's native get_mapped_doc() mapper, which checks check_permission("create")
	on the TARGET doctype before returning even an unsaved, in-memory mapped doc — confirmed
	live, a read-only Procurement Officer genuinely hit a real PermissionError here, not a
	hypothetical. Still no write/submit granted: the human reviewing the mapped form performs
	the actual save/submit themselves, matching native ERPNext "Create" button UX, so create
	is the only additional ptype this specific flow needs."""
	role = "Procurement Officer"

	if not frappe.db.exists("Role", role):
		frappe.logger().warning(f"setup_asn_grn_permissions: Role '{role}' not found, skipping")
		return

	for doctype in ["Supplier ASN", "Purchase Receipt"]:
		if not frappe.db.exists("DocType", doctype):
			frappe.logger().warning(f"setup_asn_grn_permissions: DocType '{doctype}' not found, skipping")
			continue

		frappe.db.delete("Custom DocPerm", {"parent": doctype, "role": role, "permlevel": 0})
		add_permission(doctype, role, permlevel=0)
		update_permission_property(doctype, role, 0, "read", 1)
		if doctype == "Purchase Receipt":
			update_permission_property(doctype, role, 0, "create", 1)

	frappe.db.commit()
	frappe.clear_cache()
	frappe.logger().info(
		"KCSC Proc: Supplier ASN read + Purchase Receipt read/create configured for Procurement Officer."
	)


# (role always "Procurement Officer" -- this is deliberately NOT added to
# SUPPORTING_DOCTYPES/SUPPORTING_ROLES above, since that grants all 4
# supporting roles uniformly and this decision is scoped to Procurement
# Officer alone)
MASTER_DATA_READ_WRITE_CREATE = [
	"Item", "Item Group", "Brand", "UOM", "Product Bundle", "Manufacturer",
	"Supplier", "Supplier Group", "Supplier Scorecard", "Contact", "Address",
	"Terms and Conditions", "Contract Template", "Incoterm", "Shipping Rule",
]

MASTER_DATA_READ_ONLY = [
	"Company", "Cost Center", "Account", "Currency", "Price List", "Fiscal Year",
	"Mode of Payment", "Bank Account", "Purchase Taxes and Charges Template",
	"Tax Category", "Tax Withholding Category", "Tax Withholding Group",
	"Item Tax Template", "Warehouse", "Location", "Department", "Email Template",
]


def setup_master_data_permissions():
	"""The Setup workspace page (PROC_APP_SPEC.md Section 2.12) links all 36
	master doctypes a procurement user touches, but Procurement Officer only
	had Custom DocPerm grants on 14 of them (read-only, via
	SUPPORTING_DOCTYPES/setup_supporting_doctype_permissions() above, which
	is shared with the other 3 supporting roles) -- most of the new page was
	invisible, not broken (Frappe's own workspace rendering correctly hides
	a card/link the viewing user can't read), but not genuinely usable.

	Decision (Yasser, bank context, 2026-09-12): split by who actually owns
	the doctype, not by what's technically already reachable. Procurement
	genuinely owns and maintains MASTER_DATA_READ_WRITE_CREATE (item/supplier
	masters, plus the terms/contract/shipping templates procurement authors
	itself) -- read+write+create. MASTER_DATA_READ_ONLY is finance/IT-owned
	(company, accounts, tax, warehouse/location, department, email
	templates) -- procurement needs visibility to fill out its own
	documents correctly (e.g. picking a Cost Center or Warehouse), not
	control over the record itself. Buying/Stock/Accounts Settings
	deliberately get no grant at all -- site-wide configuration, no
	procurement-specific reason to touch it from this role.

	No `submit` anywhere in either list: none of these 36 are submittable
	doctypes. No `delete` anywhere either, deliberately: a Procurement
	Officer deleting an Item or Supplier already used in historical
	Material Requests/POs/Invoices is a real, avoidable risk, not something
	this role needs for its own job -- `update_permission_property()` below
	only ever sets read/write/create, so delete stays at Custom DocPerm's
	own default (0), the same way every other function in this file already
	leaves it untouched rather than explicitly zeroing it.

	Checked before writing any of this (2026-09-12): none of the 14
	pre-existing grants were broader than this decision (all 14 were already
	read-only, matching or narrower than what's decided here for each), so
	nothing here downgrades anything -- every doctype below either gains a
	fresh grant or gets upgraded from read-only to read+write+create,
	never the reverse."""
	role = "Procurement Officer"

	if not frappe.db.exists("Role", role):
		frappe.logger().warning(f"setup_master_data_permissions: Role '{role}' not found, skipping")
		return

	for doctype in MASTER_DATA_READ_WRITE_CREATE:
		if not frappe.db.exists("DocType", doctype):
			frappe.logger().warning(f"setup_master_data_permissions: DocType '{doctype}' not found, skipping")
			continue

		frappe.db.delete("Custom DocPerm", {"parent": doctype, "role": role, "permlevel": 0})
		add_permission(doctype, role, permlevel=0)
		for ptype, value in [("read", 1), ("write", 1), ("create", 1)]:
			update_permission_property(doctype, role, 0, ptype, value)

	for doctype in MASTER_DATA_READ_ONLY:
		if not frappe.db.exists("DocType", doctype):
			frappe.logger().warning(f"setup_master_data_permissions: DocType '{doctype}' not found, skipping")
			continue

		frappe.db.delete("Custom DocPerm", {"parent": doctype, "role": role, "permlevel": 0})
		add_permission(doctype, role, permlevel=0)
		update_permission_property(doctype, role, 0, "read", 1)

	frappe.db.commit()
	frappe.clear_cache()
	frappe.logger().info(
		"KCSC Proc: Setup-page master data DocPerm configured for Procurement Officer "
		f"({len(MASTER_DATA_READ_WRITE_CREATE)} read/write/create, {len(MASTER_DATA_READ_ONLY)} read-only)."
	)

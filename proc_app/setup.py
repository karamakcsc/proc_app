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
	just not report=1."""
	grants = [
		("Material Request", "Procurement Officer"),
		("Item", "Department Officer"),
		("Item", "Procurement Officer"),
	]

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
	rule already confirmed for every other child table in this project."""
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
	had zero."""
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

	frappe.db.commit()
	frappe.clear_cache()
	frappe.logger().info("KCSC Proc: Contract read/write/create/submit configured for Procurement Officer.")

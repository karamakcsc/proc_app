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

SUPPORTING_DOCTYPES = ["Item", "Item Group", "UOM", "Warehouse", "Brand", "Company", "Department"]
SUPPORTING_ROLES = ["Department User", "Department Manager", "Department Officer", "Procurement Officer"]


def after_migrate():
	setup_material_request_permissions()
	setup_supporting_doctype_permissions()
	setup_po_amendment_permissions()


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

	frappe.db.commit()
	frappe.clear_cache()
	frappe.logger().info("KCSC Proc: Purchase Order Amendment DocPerm configured for Procurement Officer.")

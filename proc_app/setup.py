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


def after_migrate():
	setup_material_request_permissions()


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

import frappe

# DEPRECATED 2026-08-03 — no longer wired via hooks.py doc_events. See SUPPLIER_PORTAL_SPEC.md
# Section 16.4. These functions duplicated the fixture-based Notification doctype records and
# have been disabled. Left in place for reference only; do not re-enable without also removing
# the corresponding fixture Notification, or the duplication returns.


def _get_supplier_email(supplier_name):
	contact = frappe.db.get_value(
		"Dynamic Link",
		{
			"link_doctype": "Supplier",
			"link_name": supplier_name,
			"parenttype": "Contact",
		},
		"parent",
	)
	if not contact:
		return None
	return frappe.db.get_value("Contact", contact, "user")


def on_po_submit(doc, method):
	try:
		email = _get_supplier_email(doc.supplier)
		if not email:
			return

		portal_link = f"/supplier-portal/orders?name={doc.name}"
		frappe.sendmail(
			recipients=[email],
			subject=f"New Purchase Order {doc.name} issued to you",
			message=f"""
				<p>Dear {doc.supplier_name},</p>
				<p>A new Purchase Order has been issued to you.</p>
				<table>
					<tr><td><strong>PO Number:</strong></td><td>{doc.name}</td></tr>
					<tr><td><strong>Currency:</strong></td><td>{doc.currency}</td></tr>
					<tr><td><strong>Total Amount:</strong></td><td>{doc.grand_total:,.2f} {doc.currency}</td></tr>
				</table>
				<p>
					<a href="{portal_link}">View Purchase Order in Supplier Portal</a>
				</p>
			""",
		)
	except Exception:
		frappe.log_error(frappe.get_traceback(), "Portal: on_po_submit failed")


def on_invoice_submit(doc, method):
	try:
		email = _get_supplier_email(doc.supplier)
		if not email:
			return

		portal_link = f"/supplier-portal/invoices?name={doc.name}"
		frappe.sendmail(
			recipients=[email],
			subject=f"Invoice {doc.name} status update",
			message=f"""
				<p>Dear {doc.supplier_name},</p>
				<p>Your invoice <strong>{doc.name}</strong> has been submitted and is now under review.</p>
				<p>
					<a href="{portal_link}">View Invoice in Supplier Portal</a>
				</p>
			""",
		)
	except Exception:
		frappe.log_error(frappe.get_traceback(), "Portal: on_invoice_submit failed")


def on_grn_submit(doc, method):
	try:
		email = _get_supplier_email(doc.supplier)
		if not email:
			return

		portal_link = "/supplier-portal/delivery"
		frappe.sendmail(
			recipients=[email],
			subject=f"Goods Receipt {doc.name} created for your delivery",
			message=f"""
				<p>Dear {doc.supplier_name},</p>
				<p>A Goods Receipt Note (GRN) <strong>{doc.name}</strong> has been created
				for your delivery against Purchase Order <strong>{doc.purchase_order}</strong>.</p>
				<p>
					<a href="{portal_link}">Track Delivery in Supplier Portal</a>
				</p>
			""",
		)
	except Exception:
		frappe.log_error(frappe.get_traceback(), "Portal: on_grn_submit failed")

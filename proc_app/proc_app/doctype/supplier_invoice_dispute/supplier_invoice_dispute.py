import frappe
from frappe.model.document import Document

class SupplierInvoiceDispute(Document):
    def before_insert(self):
        self.submitted_on = frappe.utils.now()

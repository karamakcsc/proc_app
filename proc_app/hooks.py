app_name = "proc_app"
app_title = "KCSC Proc"
app_publisher = "KCSC — Karama Computer Services Company"
app_description = "Reusable back-office procurement system — Purchase Requisition, approval workflows, Stock Management, and procurement reporting. Multi-client, standalone-capable (no dependency on any supplier portal)."
app_email = "info@kcsc.jo"
app_license = "mit"

# List form, not a bare string -- matches how frappe/erpnext both declare
# this hook (frappe/hooks.py, erpnext/hooks.py), confirmed by reading both
# before writing this rather than following a single suggested example.
app_include_icons = [
	"/assets/proc_app/icons/proc_icons.svg",
]

after_migrate = "proc_app.setup.after_migrate"

fixtures = [
	# module="Proc App" alone would ALSO capture Supplier ASN/Supplier ASN
	# Item/Supplier Invoice Dispute -- those are file-based doctypes (their
	# own .json lives in proc_app/proc_app/doctype/) that already sync
	# automatically via frappe.model.sync.sync_all(), confirmed to run BEFORE
	# sync_fixtures() in migrate's own order (frappe/migrate.py) -- fixture-
	# tracking them too would let a stale fixture snapshot silently overwrite
	# a newer file-based doctype edit on every future migrate. Excluded
	# explicitly so this fixture stays scoped to what it's actually for: the
	# 3 doctypes that exist ONLY as database records with no file backing at
	# all, where module-based filtering is still a genuine, self-maintaining
	# improvement over the old 3-name list for any FUTURE database-only
	# doctype.
	{"dt": "DocType", "filters": [
		["module", "=", "Proc App"],
		["name", "not in", ["Supplier ASN", "Supplier ASN Item", "Supplier Invoice Dispute"]],
	]},
	# dt IN [...] captures every field on the doctypes we actually customise,
	# self-maintaining for future fields on the same doctypes (confirmed live:
	# module is None for the great majority of these, so filtering by module
	# instead would silently drop most of them -- dt is the only reliable
	# axis). One explicit exclusion: "Purchase Order-workflow_state" is NOT
	# ours -- it was auto-created by an unrelated demo Workflow ("PO WF",
	# 2026-09-02) that is not part of this project and must not ship to a
	# fresh install (see PROC_APP_SPEC.md's Contract-workflow-conflict entry
	# for the same class of issue on a different doctype).
	{"dt": "Custom Field", "filters": [
		["dt", "in", ["Material Request", "Request for Quotation", "Department", "Supplier", "Purchase Invoice", "Purchase Order", "Contract"]],
		["name", "not in", ["Purchase Order-workflow_state"]],
	]},
	# No `module` field on Role at all -- name list is the only option, and
	# roles are few and stable enough that this is a non-issue in practice.
	{"dt": "Role", "filters": [["role_name", "in", ["Department Manager", "Department Officer", "Department User", "Procurement Officer"]]]},
	# Workflow State / Workflow Action Master have no document_type field --
	# confirmed via get_meta(), not assumed -- they're generic, site-wide
	# label vocabularies shared across every workflow, not scoped to any one
	# doctype. Filtering by document_type is structurally not possible here;
	# name list is the only mechanism, same reasoning as Role above.
	{"dt": "Workflow State", "filters": [["name", "in", ["Draft", "Pending Requesting-Dept Approval", "Pending Concerned-Dept Review", "Approved - Issue", "Pending Concerned-Dept Manager Approval", "Pending Procurement Approval", "Approved - Purchase", "Pending Approval", "Terminated"]]]},
	{"dt": "Workflow Action Master", "filters": [["name", "in", ["Submit", "Approve - Issue from Stock", "Approve - Forward to Purchase", "Terminate"]]]},
	# Workflow is DELIBERATELY kept as an explicit name list, not filtered by
	# document_type -- this is the one case where a broader filter would be
	# actively dangerous, not just imprecise. This project has twice found a
	# throwaway demo Workflow silently active on a doctype we own (Contract,
	# 2026-09-06; Purchase Order/"PO WF", 2026-09-02) -- a document_type-based
	# filter would auto-sweep any FUTURE demo workflow on these same doctypes
	# straight into the fixture and ship it to production. The explicit list
	# forces a deliberate decision to add each real workflow by name.
	{"dt": "Workflow", "filters": [["name", "in", ["Material Request Approval", "Purchase Order Amendment Approval", "RFQ Approval", "Comparison Sheet Approval", "Contract Approval"]]]},
	# Report is DELIBERATELY kept as a name list, not module="Proc App" --
	# confirmed live that only 2 of our 5 real reports carry that module;
	# the other 3 (raw-SQL, non-script reports) are filed under "Buying"/
	# "Stock" by Frappe's own report-module inference. A module filter would
	# silently drop 3 of 5 real reports.
	{"dt": "Report", "filters": [["name", "in", ["Purchase Requisition Status", "Items Below Reorder Level", "Physical Count Variance", "RFQ Comparison - By Proposal", "Budget Utilisation"]]]},
	# Page fixture entry REMOVED entirely (found via a real fresh-site install
	# test, 2026-09-08): Page.validate() (frappe/core/doctype/page/page.py)
	# unconditionally throws "Not in Developer Mode" for a new Page record
	# outside developer mode, with NO exemption for frappe.flags.in_import/
	# in_migrate/in_patch at all -- unlike every other fixture-tracked doctype
	# here (Report/Workspace/Workspace Sidebar/Desktop Icon all either exempt
	# in_import explicitly or only gate an optional side-effect, never throw;
	# DocType's own guard is bypassed by custom=1). Because
	# frappe.utils.fixtures.import_fixtures() only catches ImportError/
	# DoesNotExistError per file, this ValidationError aborted the ENTIRE
	# fixture import for every file sorting after "page.json" alphabetically
	# (property_setter, report, role, workflow*, workspace*) on every single
	# fresh install AND every subsequent migrate -- confirmed by directly
	# installing all three apps on a throwaway site. Both Pages this entry
	# covered (rfq-comparison, procurement-dash) are already file-based
	# (confirmed: both have their own .json+.js under
	# proc_app/proc_app/page/) and sync automatically via
	# frappe.model.sync.sync_all(), independent of fixtures entirely -- this
	# entry was pure, actively-dangerous redundancy, not a real requirement.
	{"dt": "Workspace", "filters": [["module", "=", "Proc App"]]},
	{"dt": "Workspace Sidebar", "filters": [["module", "=", "Proc App"]]},
	{"dt": "Desktop Icon", "filters": [["link_to", "=", "Procurement"]]},
	# dt IN [...] captures exactly the same 9 Client Scripts as the old name
	# list (confirmed live, nothing foreign on any of these doctypes) --
	# self-maintaining for any future script on a doctype we already touch.
	{"dt": "Client Script", "filters": [["dt", "in", ["RFQ Comparison Sheet", "Request for Quotation", "Supplier Quotation", "Supplier ASN", "Contract", "Material Request", "Purchase Order", "Purchase Invoice"]]]},
	# NEW -- Property Setter was never fixture-tracked at all (2026-09-08
	# deployment audit finding): Contract's own field_order (the doctype's
	# entire field layout) and both custom doctypes' naming_series options
	# are Property Setters, not Custom Fields, and would not have transferred
	# to a fresh install. or_filters ORs the two conditions together: doc_type
	# IN [...] is safe for doctypes we fully own (confirmed live -- zero of
	# the site's other ~154 Property Setters carry any of these doc_types, so
	# nothing foreign gets swept in); the 3 default_print_format setters live
	# on shared, heavily ERPNext-customised doctypes (Purchase Order/Invoice,
	# RFQ) where a doc_type-based filter would also catch a large amount of
	# generic, non-project Property Setter noise (accounting_dimensions_section
	# visibility, scan_barcode, rounded_total, etc.) -- named explicitly
	# instead, the same reasoning as Report above.
	{"dt": "Property Setter", "or_filters": [
		["doc_type", "in", ["Contract", "Purchase Order Amendment", "RFQ Comparison Sheet", "RFQ Comparison Sheet Item", "Contract Fulfilment Checklist"]],
		["name", "in", ["Request for Quotation-main-default_print_format", "Purchase Invoice-main-default_print_format", "Purchase Order-main-default_print_format"]],
	]},
	# Reviewed Arabic corrections/additions to erpnext's own desk translations
	# (desk-wide audit, PROC_APP_SPEC.md Changelog -- 6 corrected collisions,
	# then 92 previously-untranslated field labels/Select options, then a
	# further 334 reviewed corrections to already-translated-but-semantically-
	# wrong strings, e.g. ID/Required By/Write Off -- 432 total) --
	# overriding/filling in via the Translation doctype rather than editing
	# erpnext's ar.csv directly, since that file is owned by erpnext and gets
	# overwritten on bench update. Filtered by source_text (self-documenting
	# here -- a reader can see exactly which strings this covers without
	# decoding an autoname) AND language="ar", explicitly, not by module or a
	# broader marker, since Translation has no module field of its own to
	# scope on. An explicit list rather than a broader language="ar" +
	# contributed=0 filter is deliberate: contributed=0 is the DEFAULT for any
	# manually-created Translation record, including one a future admin adds
	# by hand for an unrelated, un-reviewed reason through the normal desk
	# UI -- a broad filter would ship that too, indistinguishably from these
	# reviewed corrections. contributed=0 is still checked (excluding
	# contributed=1) so a future community-contributed translation for one of
	# these exact same strings can't get silently swept into this fixture and
	# shipped as if it were reviewed; it narrows the explicit list further, it
	# doesn't replace it. Same list-over-broad-filter choice this file already
	# makes for Workflow States/Actions/Reports/Roles above.
	{"dt": "Translation", "filters": [
		["language", "=", "ar"],
		["source_text", "in", ["% Amount Billed", "Accepted Qty", "Accepted Qty in Stock UOM", "Accepted Quantity", "Accepted Warehouse", "Account", "Account Currency (From)", "Account Currency (To)", "Accounting Details", "Acknowledged by Supplier", "Action if Accumulated Monthly Budget Exceeded on Actual", "Action if Accumulated Monthly Budget Exceeded on MR", "Action if Accumulated Monthly Budget Exceeded on PO", "Action if Annual Budget Exceeded on Actual", "Action if Annual Budget Exceeded on MR", "Action if Annual Budget Exceeded on PO", "Add Serial / Batch No", "Add Serial / Batch No (Rejected Qty)", "Additional Discount Amount (Company Currency)", "Address", "Address and Contact", "Address and Contacts", "Advance Paid (Company Currency)", "Advance Taxes and Charges", "Advances", "Against Blanket Order", "Alias", "Allow Alternative Item", "Allow purchase invoice creation without purchase order", "Allow purchase invoice creation without purchase receipt", "Allow Zero Valuation Rate", "Allowed to transact with", "Amendment Type", "Amount", "Applicable on booking actual expenses", "Approved", "Assigned To", "Authorised By", "Auto create assets on purchase", "Auto Created (Reorder)", "Auto re-order", "Auto Renew", "Available Qty at Target Warehouse", "Bank", "Bank Account No", "Batch No", "Billed Amount", "Billed Amt", "Billed, Received & Returned", "Billing Address", "Billing Currency", "Blanket Order", "Blanket Order Rate", "Block Supplier", "Book Advance Payments in Separate Party Account", "Budget", "Budget Against", "Budget Amount", "Budget Distribution", "Budget Distribution Total", "Budget End Date", "Budget Impact", "Budget Start Date", "Cancelled", "City", "Clearance Date", "Commercial Registration No.", "Company", "Comparison Items", "Completed", "Concerned Department", "Connections", "Consider for Tax Withholding", "Consultancy", "Consumed Items", "Contact", "Contact Email", "Contact Mobile No", "Contact Person", "Contract", "Contract Category", "Contract Value", "Control Action", "Cost Center Name", "Created On", "Credit To", "Customer Items", "Customer Provided", "Date", "Date Change", "Debit Note Issued", "Default BOM", "Default In-Transit Warehouse", "Default Warehouse", "Defaults", "Deferred Expense Account", "Delivered", "Delivered by Supplier (Drop Ship)", "Delivery Note Item", "Department", "Department Manager", "Department Officer", "Description", "Description of Change", "Details", "Difference Amount (Company Currency)", "Disable Rounded Total", "Dispute Type", "Distribution Frequency", "Document Type", "Draft", "Drop Ship", "Due Date", "Duplicate", "Duplicate Invoice", "Edit", "Edit Posting Date and Time", "Email Address", "Email ID", "Email Sent", "End Date", "End of Life", "Exchange Rate", "Expense Account", "Expense Head", "Expired", "FIFO", "Filter", "Finished Good", "Finished Good Qty", "Fulfilled", "Fulfilment Deadline", "Fulfilment Details", "Fulfilment Status", "Fulfilment Terms", "Gender", "Generated By", "Generated On", "Get Outstanding Invoices", "Get Outstanding Orders", "Grand Total (Company Currency)", "Grant Commission", "Group same items", "Half-Yearly", "Has Batch No", "Has Expiry Date", "Hold Invoice", "Hosting", "ID", "Ignore Tax Withholding Threshold", "Image", "In Transit", "In Words", "In Words (Company Currency)", "Include Exploded Items", "Include Item In Manufacturing", "Initiated", "Inspection Required before Delivery", "Inspection Required before Purchase", "Instructions", "Inter Company Invoice Reference", "Inter Company Order Reference", "Inter Company Reference", "Internal Supplier Details", "Inventory", "Inventory Valuation", "Is Fixed Asset", "Is Free Item", "Is Frozen", "Is Group Warehouse", "Is Internal Supplier", "Is Opening Entry", "Is Paid", "Is Rejected Warehouse", "Is Return (Debit Note)", "Is Subcontracted", "Is Subcontracted Item", "Is Transporter", "Issued", "Item", "Item Addition or Removal", "Item Attribute", "Item Attributes", "Item Code", "Item Defaults", "Item Name", "Item Reorder", "Item Tax Amount Included in Value", "Item Tax Template", "Items", "Landed Cost Voucher Amount", "Lapsed", "Last Purchase Rate", "Last Updated On", "Lead Time Date", "Lead Time Weight (%)", "Letter Head", "LIFO", "Likes", "Maintain Stock", "Manufacture", "Material Request Plan Item", "Menu", "Message for Supplier", "Minimum Order Qty", "Missing Items", "Monthly", "MPS", "Name", "Net Rate", "Net Total", "Net Total (Company Currency)", "Onboarding Reviewed By", "Onboarding Submitted On", "Open", "Opportunity", "Other", "Overdue", "Owner", "Packed Item", "Paid Amount (Company Currency)", "Paid From Account Type", "Paid To Account Type", "Parent Department", "Partially Fulfilled", "Partially Ordered", "Partially Received", "Party", "Party Bank Account", "Party Full Name", "Party User", "Payment Entry", "Payment Order Status", "Payment Ordered", "Payment References", "Per Received", "Per-Company Accounts", "Picked Qty", "PIN", "Portal Onboarding Status", "Posting Time", "Prevent POs", "Prevent RFQs", "Price Change", "Price List Currency", "Price List Exchange Rate", "Price List Rate", "Price List Rate (Company Currency)", "Price Weight (%)", "Prices HTML", "Primary Address", "Primary Address Preview", "Print Heading", "Printing Details", "Product Bundle", "Production Plan Item", "Project", "Projected On Hand", "Purchase Order Amendment", "Purchase Receipt", "Purchase Receipt Detail", "Purchase Receipt Item", "Purchase Taxes and Charges", "Purpose", "Qty as Per Stock UOM", "Qty as per Stock UOM", "Qty in Stock UOM", "Quality", "Quantity", "Quantity and Rate", "Quantity and Warehouse", "Quantity Change", "Quarterly", "Quote Status", "Range", "Rate", "Rate (Company Currency)", "Rate and Amount", "Rate of Stock UOM", "Rate With Margin", "Raw Materials Supplied Cost", "Reason For Putting On Hold", "Receive", "Received", "Received Amount (Company Currency)", "Received and Accepted", "Received Qty", "Received Qty in Stock UOM", "Reference", "Reference Document Type", "References", "Rejected Serial No", "Rejected Warehouse", "Release Date", "Renewed From", "Reorder Level", "Reorder level based on Warehouse", "Reorder Qty", "Request for Quotation", "Request for Quotation Item", "Request for Quotation Supplier", "Requested By", "Requesting Department", "Required By", "Required Date", "Requires Fulfilment", "Resolution Note", "Retain Sample", "Return", "Return Against Purchase Invoice", "Return Against Purchase Receipt", "Return Issued", "Return Qty from Rejected Warehouse", "Returned Qty", "Revision Of", "RFQ Comparison Sheet", "Rounded Total", "Rounded Total (Company Currency)", "Safety Stock", "Sales", "Sales Order", "Sales Order Item", "Select Dispatch Address", "Select Supplier Address", "Selection Finalized By", "Selection Finalized On", "Send Email", "Sender", "Serial No", "Serial Nos / Batches", "Serial Number Series", "Set Accepted Warehouse", "Set From Warehouse", "Set Reserve Warehouse", "Set Target Warehouse", "Settings", "Shelf Life In Days", "Shipment/Tracking Reference", "Shipped", "Signed", "Signed By (Company)", "Signed On", "Signee", "Signee (Company)", "Signee Details", "SLA", "Source Material Request", "Source Warehouse", "Standard Selling Rate", "Stock Levels", "Stock Levels HTML", "Stock Qty", "Stock UOM", "Stop", "Stopped", "Subcontract BOM", "Subject", "Submit", "Submitted", "Submitted On", "Subscription", "Supplier Acknowledged On", "Supplier Acknowledgment Note", "Supplier ASN", "Supplier Delivery Note", "Supplier Invoice Date", "Supplier Invoice Dispute", "Supplier Quotation", "Supplier Quotation Item", "Supplier Type", "Supplier Warehouse", "Suppliers", "Supply", "Tags", "Target Warehouse", "Tax", "Tax Breakup", "Tax Identification", "Tax Issue", "Tax Withholding Category", "Tax Withholding Group", "Taxes and Charges Deducted", "Taxes and Charges Deducted (Company Currency)", "Terminated By", "Termination Date", "Termination Reason", "Terms", "Time", "Title", "To Bill", "To Receive", "To Receive and Bill", "Total", "Total (Company Currency)", "Total Advance", "Total Allocated Amount (Company Currency)", "Total Projected Qty", "Total Taxes and Charges", "Totals (Company Currency)", "Transaction ID", "Transfer Status", "Transferred", "Transit", "Transporter Name", "Tree Details", "Unallocated Amount", "Under Review", "Unfulfilled", "Unsigned", "UOM Conversion Details", "Update Auto Repeat Reference", "Update Outstanding for Self", "Variant Attributes", "Variant Based On", "Variant Of", "Vehicle Date", "Vehicle Number", "Warehouse", "Warehouse and Reference", "Warehouse Contact Info", "Warehouse Settings", "Warn POs", "Warn RFQs", "Write Off", "Write Off Account", "Write Off Amount", "Write Off Amount (Company Currency)", "Write Off Cost Center", "Write Off Difference Amount", "Writeoff", "Wrong Amount", "Yearly"]],
		["contributed", "=", 0],
	]},
]

doc_events = {
	"Material Request": {
		"before_validate": [
			"proc_app.material_request_hooks.validate_department_company",
			"proc_app.material_request_hooks.propagate_cost_center",
		],
		"on_update": "proc_app.material_request_hooks.on_material_request_update",
	},
}

# Apps
# ------------------

# required_apps = []

# Each item in the list will be shown as an app in the apps page
# add_to_apps_screen = [
# 	{
# 		"name": "proc_app",
# 		"logo": "/assets/proc_app/logo.png",
# 		"title": "KCSC Proc",
# 		"route": "/proc_app",
# 		"has_permission": "proc_app.api.permission.has_app_permission"
# 	}
# ]

# Includes in <head>
# ------------------

# include js, css files in header of desk.html
# app_include_css = "/assets/proc_app/css/proc_app.css"
# app_include_js = "/assets/proc_app/js/proc_app.js"

# include js, css files in header of web template
# web_include_css = "/assets/proc_app/css/proc_app.css"
# web_include_js = "/assets/proc_app/js/proc_app.js"

# include custom scss in every website theme (without file extension ".scss")
# website_theme_scss = "proc_app/public/scss/website"

# include js, css files in header of web form
# webform_include_js = {"doctype": "public/js/doctype.js"}
# webform_include_css = {"doctype": "public/css/doctype.css"}

# include js in page
# page_js = {"page" : "public/js/file.js"}

# include js in doctype views
# doctype_js = {"doctype" : "public/js/doctype.js"}
# doctype_list_js = {"doctype" : "public/js/doctype_list.js"}
# doctype_tree_js = {"doctype" : "public/js/doctype_tree.js"}
# doctype_calendar_js = {"doctype" : "public/js/doctype_calendar.js"}

# Svg Icons
# ------------------
# include app icons in desk
# app_include_icons = "proc_app/public/icons.svg"

# Home Pages
# ----------

# application home page (will override Website Settings)
# home_page = "login"

# website user home page (by Role)
# role_home_page = {
# 	"Role": "home_page"
# }

# Generators
# ----------

# automatically create page for each record of this doctype
# website_generators = ["Web Page"]

# automatically load and sync documents of this doctype from downstream apps
# importable_doctypes = [doctype_1]

# Jinja
# ----------

# add methods and filters to jinja environment
# jinja = {
# 	"methods": "proc_app.utils.jinja_methods",
# 	"filters": "proc_app.utils.jinja_filters"
# }

# Installation
# ------------

# before_install = "proc_app.install.before_install"
# after_install = "proc_app.install.after_install"

# Uninstallation
# ------------

# before_uninstall = "proc_app.uninstall.before_uninstall"
# after_uninstall = "proc_app.uninstall.after_uninstall"

# Integration Setup
# ------------------
# To set up dependencies/integrations with other apps
# Name of the app being installed is passed as an argument

# before_app_install = "proc_app.utils.before_app_install"
# after_app_install = "proc_app.utils.after_app_install"

# Integration Cleanup
# -------------------
# To clean up dependencies/integrations with other apps
# Name of the app being uninstalled is passed as an argument

# before_app_uninstall = "proc_app.utils.before_app_uninstall"
# after_app_uninstall = "proc_app.utils.after_app_uninstall"

# Build
# ------------------
# To hook into the build process

# after_build = "proc_app.build.after_build"

# Desk Notifications
# ------------------
# See frappe.core.notifications.get_notification_config

# notification_config = "proc_app.notifications.get_notification_config"

# Permissions
# -----------
# Permissions evaluated in scripted ways

# permission_query_conditions = {
# 	"Event": "frappe.desk.doctype.event.event.get_permission_query_conditions",
# }
#
# has_permission = {
# 	"Event": "frappe.desk.doctype.event.event.has_permission",
# }

# Document Events
# ---------------
# Hook on document methods and events

# doc_events = {
# 	"*": {
# 		"on_update": "method",
# 		"on_cancel": "method",
# 		"on_trash": "method"
# 	}
# }

# Scheduled Tasks
# ---------------

scheduler_events = {
	"daily": [
		"proc_app.api.contracts.check_contract_expiry"
	]
}

# Testing
# -------

# before_tests = "proc_app.install.before_tests"

# Extend DocType Class
# ------------------------------
#
# Specify custom mixins to extend the standard doctype controller.
# extend_doctype_class = {
# 	"Task": "proc_app.custom.task.CustomTaskMixin"
# }

# Overriding Methods
# ------------------------------
#
# override_whitelisted_methods = {
# 	"frappe.desk.doctype.event.event.get_events": "proc_app.event.get_events"
# }
#
# each overriding function accepts a `data` argument;
# generated from the base implementation of the doctype dashboard,
# along with any modifications made in other Frappe apps
# override_doctype_dashboards = {
# 	"Task": "proc_app.task.get_dashboard_data"
# }

# exempt linked doctypes from being automatically cancelled
#
# auto_cancel_exempted_doctypes = ["Auto Repeat"]

# Ignore links to specified DocTypes when deleting documents
# -----------------------------------------------------------

# ignore_links_on_delete = ["Communication", "ToDo"]

# Request Events
# ----------------
# before_request = ["proc_app.utils.before_request"]
# after_request = ["proc_app.utils.after_request"]

# Job Events
# ----------
# before_job = ["proc_app.utils.before_job"]
# after_job = ["proc_app.utils.after_job"]

# User Data Protection
# --------------------

# user_data_fields = [
# 	{
# 		"doctype": "{doctype_1}",
# 		"filter_by": "{filter_by}",
# 		"redact_fields": ["{field_1}", "{field_2}"],
# 		"partial": 1,
# 	},
# 	{
# 		"doctype": "{doctype_2}",
# 		"filter_by": "{filter_by}",
# 		"partial": 1,
# 	},
# 	{
# 		"doctype": "{doctype_3}",
# 		"strict": False,
# 	},
# 	{
# 		"doctype": "{doctype_4}"
# 	}
# ]

# Authentication and authorization
# --------------------------------

# auth_hooks = [
# 	"proc_app.auth.validate"
# ]

# Automatically update python controller files with type annotations for this app.
# export_python_type_annotations = True

# default_log_clearing_doctypes = {
# 	"Logging DocType Name": 30  # days to retain logs
# }

# Translation
# ------------
# List of apps whose translatable strings should be excluded from this app's translations.
# ignore_translatable_strings_from = []


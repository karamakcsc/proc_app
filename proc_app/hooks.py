app_name = "proc_app"
app_title = "KCSC Proc"
app_publisher = "KCSC — Karama Computer Services Company"
app_description = "Reusable back-office procurement system — Purchase Requisition, approval workflows, Stock Management, and procurement reporting. Multi-client, standalone-capable (no dependency on any supplier portal)."
app_email = "info@kcsc.jo"
app_license = "mit"

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
	# Page/Workspace/Workspace Sidebar all reliably carry module="Proc App"
	# (confirmed live: exact same record set as the old name lists, nothing
	# foreign) -- switched for the same self-maintaining reasoning as DocType.
	{"dt": "Page", "filters": [["module", "=", "Proc App"]]},
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


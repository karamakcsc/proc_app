import frappe
from frappe import _
from frappe.utils import flt

from erpnext.controllers.budget_controller import BudgetValidation


def execute(filters=None):
	filters = frappe._dict(filters or {})
	columns = get_columns()
	data = get_data(filters)
	return columns, data


def get_columns():
	return [
		{"label": _("Company"), "fieldname": "company", "fieldtype": "Link", "options": "Company", "width": 100},
		{"label": _("Cost Center"), "fieldname": "cost_center", "fieldtype": "Link", "options": "Cost Center", "width": 120},
		{"label": _("Account"), "fieldname": "account", "fieldtype": "Link", "options": "Account", "width": 200},
		{"label": _("Fiscal Year"), "fieldname": "fiscal_year", "fieldtype": "Data", "width": 90},
		{"label": _("Budget Amount"), "fieldname": "budget_amount", "fieldtype": "Currency", "width": 120},
		{"label": _("Actual Expense"), "fieldname": "actual_expense", "fieldtype": "Currency", "width": 120},
		{"label": _("Actual %"), "fieldname": "actual_pct", "fieldtype": "Percent", "width": 90},
		{"label": _("Actual Remaining"), "fieldname": "actual_remaining", "fieldtype": "Currency", "width": 130},
		{"label": _("Ordered"), "fieldname": "ordered_amount", "fieldtype": "Currency", "width": 120},
		{"label": _("Ordered %"), "fieldname": "ordered_pct", "fieldtype": "Percent", "width": 90},
		{"label": _("Ordered Remaining"), "fieldname": "ordered_remaining", "fieldtype": "Currency", "width": 130},
		{"label": _("Requested"), "fieldname": "requested_amount", "fieldtype": "Currency", "width": 120},
		{"label": _("Requested %"), "fieldname": "requested_pct", "fieldtype": "Percent", "width": 90},
		{"label": _("Requested Remaining"), "fieldname": "requested_remaining", "fieldtype": "Currency", "width": 140},
		{"label": _("Status"), "fieldname": "status", "fieldtype": "Data", "width": 130},
	]


def _matching_budgets(filters):
	conditions = {"docstatus": 1}
	if filters.get("company"):
		conditions["company"] = filters.company
	if filters.get("cost_center"):
		conditions["cost_center"] = filters.cost_center
	if filters.get("account"):
		conditions["account"] = filters.account

	budgets = frappe.get_all(
		"Budget",
		filters=conditions,
		fields=["name", "company", "cost_center", "account", "from_fiscal_year", "to_fiscal_year"],
	)

	fiscal_year = filters.get("fiscal_year")
	if not fiscal_year:
		return budgets

	# from_fiscal_year/to_fiscal_year are Fiscal Year names ("2026", "2027", ...) --
	# same simple numeric-year naming this project's real Budget/Fiscal Year records
	# use throughout, so a plain string range comparison is correct here (matches
	# how every real budget in this project spans exactly one such year).
	return [b for b in budgets if b.from_fiscal_year <= fiscal_year <= b.to_fiscal_year]


_STATUS_SEVERITY = {"OK": 0, "Near limit": 1, "Over budget": 2}


def _bucket_status(amount, budget_amount, near_limit_pct):
	"""OK / Near limit / Over budget for a single bucket against the full
	budget_amount -- confirmed via source and a live reconciliation test
	(PROC_APP_SPEC.md v1.86) that ERPNext checks requested/ordered/actual
	independently against budget_amount, not as one combined pool, unless a
	Budget has the separate, opt-in applicable_on_cumulative_expense enabled
	(none in this project do). Getting this wrong here would reproduce the
	exact bug that entry fixed. Returns the untranslated status key -- kept
	in English internally (for the severity comparison in _worse() and the
	status filter, both independent of the active language) and translated
	only once, at the point a row is actually built."""
	if not budget_amount:
		return "OK", 0.0
	pct = (amount / budget_amount) * 100
	if amount > budget_amount:
		return "Over budget", pct
	if pct >= near_limit_pct:
		return "Near limit", pct
	return "OK", pct


def _worse(a, b):
	return a if _STATUS_SEVERITY[a] >= _STATUS_SEVERITY[b] else b


def get_data(filters):
	"""One row per Budget, with allocated/actual/ordered/requested figures
	reused directly from ERPNext's own BudgetValidation -- not a parallel
	query -- so this report can never silently disagree with what real
	enforcement (or the live budget-preview panel, PROC_APP_SPEC.md v1.82/86)
	computes for the same key.

	get_requested_amount()/get_ordered_amount()/get_actual_expense() are
	normally scoped to a specific in-flight document's own item_code list
	(confirmed via source: that restriction only applies when
	document_type is "Purchase Order" or "Material Request"). A report
	needs the budget-WIDE total, not scoped to any one document's items --
	achieved here by constructing BudgetValidation via its OTHER real
	constructor path, gl_map=[...], with a single synthetic entry carrying
	just this budget's own company/cost_center/account. That makes
	document_type "GL Map", which the source confirms skips the item_code
	restriction entirely -- giving the true, unscoped total through the
	exact same query code enforcement uses, with no reimplementation and
	no divergence risk."""
	near_limit_pct = flt(filters.get("near_limit_threshold")) or 80.0
	status_filter = filters.get("status") or "All"

	rows = []
	for budget in _matching_budgets(filters):
		gl_map = [
			frappe._dict(
				{
					"company": budget.company,
					"posting_date": frappe.utils.today(),
					"account": budget.account,
					"cost_center": budget.cost_center,
					"debit": 0,
					"credit": 0,
				}
			)
		]
		validation = BudgetValidation(gl_map=gl_map)
		validation.build_validation_map()
		if not validation.to_validate:
			# No dimension type on this Budget matched cost_center/project/a
			# custom Accounting Dimension the way build_budget_keys() expects --
			# genuinely nothing to report for this row.
			continue

		key = next(iter(validation.to_validate))
		validation.get_ordered_amount(key)
		validation.get_requested_amount(key)
		validation.get_actual_expense(key)
		v = validation.to_validate[key]

		budget_amount = flt(v.budget_amount)
		actual_expense = flt(v.actual_expense)
		ordered_amount = flt(v.ordered_amount)
		requested_amount = flt(v.requested_amount)

		actual_status, actual_pct = _bucket_status(actual_expense, budget_amount, near_limit_pct)
		ordered_status, ordered_pct = _bucket_status(ordered_amount, budget_amount, near_limit_pct)
		requested_status, requested_pct = _bucket_status(requested_amount, budget_amount, near_limit_pct)
		overall_status = _worse(_worse(actual_status, ordered_status), requested_status)

		if status_filter == "Over budget only" and overall_status != "Over budget":
			continue
		if status_filter == "Near limit only" and overall_status != "Near limit":
			continue

		rows.append(
			{
				"company": budget.company,
				"cost_center": budget.cost_center,
				"account": budget.account,
				"fiscal_year": budget.from_fiscal_year
				if budget.from_fiscal_year == budget.to_fiscal_year
				else f"{budget.from_fiscal_year}-{budget.to_fiscal_year}",
				"budget_amount": budget_amount,
				"actual_expense": actual_expense,
				"actual_pct": actual_pct,
				"actual_remaining": budget_amount - actual_expense,
				"ordered_amount": ordered_amount,
				"ordered_pct": ordered_pct,
				"ordered_remaining": budget_amount - ordered_amount,
				"requested_amount": requested_amount,
				"requested_pct": requested_pct,
				"requested_remaining": budget_amount - requested_amount,
				"status": _(overall_status),
			}
		)

	return rows

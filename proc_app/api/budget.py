import json

import frappe
from frappe.utils import flt, today

from erpnext.controllers.budget_controller import BudgetValidation
from erpnext.stock.get_item_details import get_item_details


def _resolve_item_row(item, company, default_cost_center):
	"""Resolves expense_account via ERPNext's own get_item_details() -- the exact
	same Item -> Item Group -> Company fallback chain a real submit would use
	(get_item_details.py, traced and confirmed multiple times this project) --
	never reimplemented here. cost_center is whatever the row/document already
	picked; get_item_details() also returns one, but a real Material Request
	Item's cost_center is the requester's own explicit choice (or the document's
	set_cost_center default), not something this preview should override."""
	qty = flt(item.get("qty")) or 1.0
	args = frappe._dict(
		{
			"item_code": item["item_code"],
			"company": company,
			"doctype": "Material Request",
			"material_request_type": "Purchase",
			"transaction_date": today(),
			"conversion_rate": 1,
			"currency": frappe.get_cached_value("Company", company, "default_currency"),
			"qty": qty,
		}
	)
	details = get_item_details(args)
	rate = flt(item.get("rate"))
	if not rate:
		rate = flt(details.get("rate")) or flt(details.get("price_list_rate"))
	cost_center = item.get("cost_center") or default_cost_center or details.get("cost_center")
	return frappe._dict(
		{
			"item_code": item["item_code"],
			"qty": qty,
			"rate": rate,
			"amount": qty * rate,
			"cost_center": cost_center,
			"expense_account": details.get("expense_account"),
		}
	)


def _classify(remaining_annual, remaining_monthly, action_annual, action_monthly):
	"""Mirrors erpnext.controllers.budget_controller.BudgetValidation's own
	handle_individual_doctype_action(): annual and monthly are two independent
	thresholds, each with its own configured action (Stop/Warn/Ignore). Whichever
	threshold is breached with the more severe action (Stop > Warn > Ignore)
	determines the overall status -- if neither is breached, "ok"."""
	breaches = []
	if remaining_annual < 0:
		breaches.append(action_annual)
	if remaining_monthly < 0:
		breaches.append(action_monthly)
	if not breaches:
		return "ok"
	if "Stop" in breaches:
		return "exceeded"
	if "Warn" in breaches:
		return "warning"
	return "ok"  # only "Ignore" actions breached -- no visible consequence at submit either


@frappe.whitelist()
def get_budget_preview(company, items, cost_center=None):
	"""Returns budget availability for the (cost_center, expense_account) keys
	implied by the given draft item rows. Reuses BudgetValidation so the figures
	shown match what enforcement will actually compute — deliberately NOT a
	separate query, which could disagree with the engine that blocks submission.

	`items` is a JSON-encoded list of {item_code, qty, rate?, cost_center?} --
	rate/cost_center are optional per row; a missing rate falls back to the
	item's own price list rate (best-effort estimate, matching what the desk/
	portal form would show before a user overrides it), and a missing
	cost_center falls back to the `cost_center` param (mirroring the document-
	level "set_cost_center" default).

	Builds a temporary, never-inserted Material Request purely so
	BudgetValidation can be constructed against it exactly the way real
	enforcement is -- only build_validation_map() is called, never
	validate_for_overbooking(), which would frappe.throw() on a breach.

	get_ordered_amount()/get_requested_amount()/get_actual_expense() only ever
	count already-submitted documents (docstatus=1) -- since this draft isn't
	submitted, its own row amounts are added on top of the queried
	requested_amount here, which is what makes this a genuine "if I submit this
	now" preview rather than a stale "before this request existed" one.
	"""
	if isinstance(items, str):
		items = json.loads(items)
	if not items:
		return []

	item_rows = [_resolve_item_row(i, company, cost_center) for i in items]

	draft_keys = set()
	for row in item_rows:
		if row.cost_center and row.expense_account:
			draft_keys.add(("cost_center", row.cost_center, row.expense_account))

	if not draft_keys:
		return []

	doc = frappe.get_doc(
		{
			"doctype": "Material Request",
			"material_request_type": "Purchase",
			"company": company,
			"transaction_date": today(),
			"items": item_rows,
		}
	)

	validation = BudgetValidation(doc=doc)
	validation.build_validation_map()

	results = []
	seen_keys = set()
	for key, v in validation.to_validate.items():
		dimension_field, dimension_value, account = key
		seen_keys.add(key)

		validation.get_ordered_amount(key)
		validation.get_requested_amount(key)
		validation.get_actual_expense(key)

		draft_amount = sum(flt(row.amount) for row in v.items_to_process)
		requested_amount = flt(v.requested_amount) + draft_amount
		ordered_amount = flt(v.ordered_amount)
		actual_expense = flt(v.actual_expense)
		budget_amount = flt(v.budget_amount)
		accumulated_monthly_budget = flt(v.accumulated_monthly_budget)

		used = requested_amount + ordered_amount + actual_expense
		remaining_annual = budget_amount - used
		remaining_monthly = accumulated_monthly_budget - used

		status = _classify(
			remaining_annual,
			remaining_monthly,
			v.budget_doc.action_if_annual_budget_exceeded_on_mr,
			v.budget_doc.action_if_accumulated_monthly_budget_exceeded_on_mr,
		)

		results.append(
			{
				"cost_center": dimension_value,
				"account": account,
				"budget_amount": budget_amount,
				"actual_expense": actual_expense,
				"ordered_amount": ordered_amount,
				"requested_amount": requested_amount,
				"accumulated_monthly_budget": accumulated_monthly_budget,
				"remaining": remaining_annual,
				"remaining_monthly": remaining_monthly,
				"status": status,
			}
		)

	for dimension_field, dimension_value, account in draft_keys - seen_keys:
		results.append(
			{
				"cost_center": dimension_value,
				"account": account,
				"budget_amount": None,
				"status": "no_budget",
				"message": f"No budget configured for cost center '{dimension_value}' and account '{account}'.",
			}
		)

	return results

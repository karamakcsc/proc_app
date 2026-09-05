import json

import frappe
from frappe.utils import flt, today

import erpnext
from erpnext.controllers.budget_controller import BudgetValidation
from erpnext.stock.get_item_details import get_item_details

# One function genuinely is cleaner than three: the core algorithm (build a
# temporary, never-inserted doc -> BudgetValidation.build_validation_map() ->
# per-key before/after split -> classify off remaining_after -> a no_budget
# fallback for unmatched keys) is identical across all three doctypes --
# investigated first, not assumed: BudgetValidation.__init__() only ever reads
# doc.get("doctype")/.get("company")/.get("transaction_date")/.items, so the
# same minimal, unvalidated in-memory doc works for all three (no supplier,
# no mandatory fields needed, since .insert()/.validate() are never called).
# What genuinely differs is a small, explicit set of per-doctype facts, kept
# here rather than scattered through if/elif branches in the body below.
_DOCTYPE_CONFIG = {
	"Material Request": {
		# Contributes to the REQUESTED bucket (get_requested_amount()) once
		# submitted -- a Material Request's own amount is a request, not yet a
		# commitment.
		"action_annual_field": "action_if_annual_budget_exceeded_on_mr",
		"action_monthly_field": "action_if_accumulated_monthly_budget_exceeded_on_mr",
		"draft_amount_key": "this_request_amount",
		"own_bucket": "requested_amount",
		"doc_defaults": {"material_request_type": "Purchase"},
	},
	"Purchase Order": {
		# Contributes to the ORDERED bucket (get_ordered_amount()) once
		# submitted -- a genuine commitment to a supplier, not just a request.
		# Action is Stop on both thresholds in this project's real budgets
		# (confirmed via live Budget records), unlike MR's Warn.
		"action_annual_field": "action_if_annual_budget_exceeded_on_po",
		"action_monthly_field": "action_if_accumulated_monthly_budget_exceeded_on_po",
		"draft_amount_key": "this_order_amount",
		"own_bucket": "ordered_amount",
		"doc_defaults": {},
	},
	"Purchase Invoice": {
		# Contributes to the ACTUAL EXPENSE bucket -- but only once genuinely
		# posted to the GL (erpnext.accounts.general_ledger's own
		# BudgetValidation(gl_map=...) call, confirmed via source, not
		# Purchase Invoice.on_submit() itself). A draft/unsubmitted invoice has
		# no GL Entries yet, so get_actual_expense()'s query never sees it --
		# same "not yet counted" situation as MR/PO, just a different real-
		# world bucket it will eventually land in.
		"action_annual_field": "action_if_annual_budget_exceeded",
		"action_monthly_field": "action_if_accumulated_monthly_budget_exceeded",
		"draft_amount_key": "this_invoice_amount",
		"own_bucket": "actual_expense",
		"doc_defaults": {},
	},
}

_STATUS_SEVERITY = {"ok": 0, "warning": 1, "exceeded": 2}


def _resolve_item_row(item, company, default_cost_center, doctype):
	"""Resolves expense_account via ERPNext's own get_item_details() -- the exact
	same Item -> Item Group -> Company fallback chain a real submit would use
	(get_item_details.py, traced and confirmed multiple times this project) --
	never reimplemented here. Passing the real target doctype (rather than
	always hardcoding "Material Request") matters: get_item_details() branches
	on it for UOM selection (purchase_uom for Purchase Order/Purchase Invoice,
	the same as Material Request type "Purchase") and other doctype-specific
	behaviour -- confirmed via source, not assumed to be harmless either way.
	cost_center is whatever the row/document already picked; get_item_details()
	also returns one, but a real item row's cost_center is the user's own
	explicit choice (or the document's own cost center default), not something
	this preview should override.

	Known, accepted limitation for Purchase Invoice specifically (found via a
	live reconciliation test, not guessed): the stock-item override just below
	replicates set_expense_account()'s common, standalone-new-invoice case --
	it does not model is_opening="Yes" (which exempts the override, but then
	genuinely cannot use a P&L account like most expense accounts at all --
	confirmed live, ERPNext itself rejects that combination) or a linked
	Purchase Receipt/drop-ship item (which route to their own, different
	accounts). This preview is built for the case a user is actually live in
	while typing a new, standalone invoice; those other paths are rare enough,
	and different enough, that a live preview reflecting the common case
	honestly is more useful than a parallel reimplementation of every branch
	set_expense_account() has."""
	qty = flt(item.get("qty")) or 1.0
	args = frappe._dict(
		{
			"item_code": item["item_code"],
			"company": company,
			"doctype": doctype,
			"transaction_date": today(),
			"conversion_rate": 1,
			"currency": frappe.get_cached_value("Company", company, "default_currency"),
			"qty": qty,
		}
	)
	args.update(_DOCTYPE_CONFIG[doctype]["doc_defaults"])
	details = get_item_details(args)
	rate = flt(item.get("rate"))
	if not rate:
		rate = flt(details.get("rate")) or flt(details.get("price_list_rate"))
	cost_center = item.get("cost_center") or default_cost_center or details.get("cost_center")
	expense_account = details.get("expense_account")

	if doctype == "Purchase Invoice":
		# get_item_details() is NOT what actually resolves expense_account for
		# a real Purchase Invoice -- Purchase Invoice has its own dedicated
		# controller method, set_expense_account() (purchase_invoice.py),
		# which unconditionally overrides a stock item's expense_account to
		# the company's own "Stock Received But Not Billed" account whenever
		# perpetual inventory is enabled, is_opening is "No", it's not a fixed
		# asset, and there's no linked Purchase Receipt/drop-ship item --
		# confirmed via source AND via a live reconciliation test that first
		# used the un-corrected version of this function: a genuinely
		# submitted Purchase Invoice landed on account 2210 (Stock Received
		# But Not Billed), not the 5208 Item-Group-configured account
		# get_item_details() alone would suggest. Replicated here for the
		# common, standalone-invoice case this preview actually serves.
		item_doc = frappe.get_cached_doc("Item", item["item_code"])
		if (
			item_doc.is_stock_item
			and not item_doc.is_fixed_asset
			and erpnext.is_perpetual_inventory_enabled(company)
		):
			stock_not_billed = frappe.get_cached_value("Company", company, "stock_received_but_not_billed")
			if stock_not_billed:
				expense_account = stock_not_billed

	return frappe._dict(
		{
			"item_code": item["item_code"],
			"qty": qty,
			"rate": rate,
			"amount": qty * rate,
			"cost_center": cost_center,
			"expense_account": expense_account,
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


def _worse_status(a, b):
	return a if _STATUS_SEVERITY[a] >= _STATUS_SEVERITY[b] else b


@frappe.whitelist()
def get_budget_preview(doctype, company, items, cost_center=None):
	"""Returns budget availability for the (cost_center, expense_account) keys
	implied by the given draft item rows, for Material Request, Purchase Order,
	or Purchase Invoice. Reuses BudgetValidation so the figures shown match
	what enforcement will actually compute — deliberately NOT a separate query,
	which could disagree with the engine that blocks submission.

	`items` is a JSON-encoded list of {item_code, qty, rate?, cost_center?} --
	rate/cost_center are optional per row; a missing rate falls back to the
	item's own price list rate (best-effort estimate, matching what the desk/
	portal form would show before a user overrides it), and a missing
	cost_center falls back to the `cost_center` param (mirroring each
	doctype's own document-level cost center default: Material Request's
	custom `set_cost_center`, or Purchase Order/Purchase Invoice's own native
	`cost_center` field).

	Builds a temporary, never-inserted document of the given doctype purely so
	BudgetValidation can be constructed against it exactly the way real
	enforcement is -- only build_validation_map() is called, never
	validate_for_overbooking(), which would frappe.throw() on a breach.

	get_ordered_amount()/get_requested_amount()/get_actual_expense() only ever
	count already-submitted documents (docstatus=1) -- this draft isn't one of
	them, so its own row amounts are returned separately under a doctype-
	specific key (this_request_amount / this_order_amount / this_invoice_amount)
	rather than folded into the queried figures, keeping them honest (committed
	spend that genuinely exists) while remaining_after still reflects what
	would happen if this draft were submitted now.

	remaining_before/remaining_after are computed from THIS doctype's own
	bucket only (requested for MR, ordered for PO, actual for PI) against the
	full budget_amount -- confirmed via source and a live reconciliation test
	that ERPNext checks each bucket independently, not as one shared pool; the
	other two buckets are still returned for context (what else this budget
	has absorbed elsewhere) but never subtracted from this doctype's own
	remaining figure. status also folds in the separate, opt-in "cumulative"
	check (applicable_on_cumulative_expense) when a Budget has it enabled,
	since that genuinely does sum all three buckets together -- taking
	whichever of the two checks is more severe.
	"""
	if doctype not in _DOCTYPE_CONFIG:
		frappe.throw(f"Budget preview is not supported for doctype {doctype}.")
	config = _DOCTYPE_CONFIG[doctype]

	if isinstance(items, str):
		items = json.loads(items)
	if not items:
		return []

	item_rows = [_resolve_item_row(i, company, cost_center, doctype) for i in items]

	draft_keys = set()
	for row in item_rows:
		if row.cost_center and row.expense_account:
			draft_keys.add(("cost_center", row.cost_center, row.expense_account))

	if not draft_keys:
		return []

	if doctype == "Purchase Invoice":
		# BudgetValidation.build_item_keys() only ever populates self.item_map
		# from self.doc.items when document_type is "Purchase Order" or
		# "Material Request" -- confirmed via source, Purchase Invoice is not
		# in that list at all. The real actual-expense check only ever runs
		# against genuine GL Entries (erpnext.accounts.general_ledger's own
		# BudgetValidation(gl_map=...) call at GL posting time), which a draft,
		# unsubmitted invoice doesn't have yet. Built here as a *synthetic*
		# gl_map -- one entry per resolved row, shaped exactly like the real
		# GL Entry fields build_item_keys()'s own "GL Map" branch reads
		# (company, posting_date, account, cost_center, debit, credit) -- so
		# the exact same aggregation code below applies unchanged.
		gl_map = [
			frappe._dict(
				{
					"company": company,
					"posting_date": today(),
					"account": row.expense_account,
					"cost_center": row.cost_center,
					"debit": row.amount,
					"credit": 0,
				}
			)
			for row in item_rows
			if row.cost_center and row.expense_account
		]
		validation = BudgetValidation(gl_map=gl_map)
	else:
		doc_dict = {
			"doctype": doctype,
			"company": company,
			"transaction_date": today(),
			"items": item_rows,
		}
		doc_dict.update(config["doc_defaults"])
		doc = frappe.get_doc(doc_dict)
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

		# draft_amount kept separate from the queried figures -- those are
		# committed spend that already exists (other submitted documents),
		# draft_amount is only what THIS draft would add if submitted now.
		if doctype == "Purchase Invoice":
			# initialize_dict() names this gl_to_process for a GL Map, and
			# each synthetic entry carries debit/credit rather than amount.
			draft_amount = sum(flt(x.debit) - flt(x.credit) for x in v.gl_to_process)
		else:
			draft_amount = sum(flt(row.amount) for row in v.items_to_process)
		requested_amount = flt(v.requested_amount)
		ordered_amount = flt(v.ordered_amount)
		actual_expense = flt(v.actual_expense)
		budget_amount = flt(v.budget_amount)
		accumulated_monthly_budget = flt(v.accumulated_monthly_budget)

		# CRITICAL, found only by reconciling a live PO-stage test against real
		# enforcement: requested/ordered/actual are each checked INDEPENDENTLY
		# against the FULL budget_amount -- handle_material_request_overlimit()/
		# handle_purchase_order_overlimit()/handle_actual_expense_overlimit()
		# each pass only their OWN bucket's existing_amt to
		# handle_individual_doctype_action(), which computes
		# "(existing_amt + current_amt) - budget_amt" using nothing else. They
		# are only ever summed together by a distinct, opt-in mechanism --
		# handle_cumulative_overlimit(), gated on applicable_on_cumulative_expense,
		# worded "collectively exceeded" in its own messages, using its own
		# separate action fields -- which none of this project's real Budget
		# records have enabled. An earlier version of this function summed all
		# three buckets into one shared "used" total unconditionally, which
		# reconciled fine only by coincidence in every prior MR-only test
		# (ordered_amount/actual_expense were always 0 there) -- it disagreed
		# with a real PO submission the moment an unrelated Material Request's
		# own requested_amount was nonzero for the same key, exactly the
		# silent-mismatch failure mode this whole feature exists to prevent.
		bucket_values = {
			"requested_amount": requested_amount,
			"ordered_amount": ordered_amount,
			"actual_expense": actual_expense,
		}
		own_amount_before = bucket_values[config["own_bucket"]]
		remaining_before = budget_amount - own_amount_before
		remaining_after = remaining_before - draft_amount

		monthly_remaining_before = accumulated_monthly_budget - own_amount_before
		monthly_remaining_after = monthly_remaining_before - draft_amount

		status = _classify(
			remaining_after,
			monthly_remaining_after,
			v.budget_doc.get(config["action_annual_field"]),
			v.budget_doc.get(config["action_monthly_field"]),
		)

		if v.budget_doc.get("applicable_on_cumulative_expense"):
			combined_after = requested_amount + ordered_amount + actual_expense + draft_amount
			cumulative_status = _classify(
				budget_amount - combined_after,
				accumulated_monthly_budget - combined_after,
				v.budget_doc.get("action_if_annual_exceeded_on_cumulative_expense"),
				v.budget_doc.get("action_if_accumulated_monthly_exceeded_on_cumulative_expense"),
			)
			status = _worse_status(status, cumulative_status)

		results.append(
			{
				"cost_center": dimension_value,
				"account": account,
				"budget_amount": budget_amount,
				"actual_expense": actual_expense,
				"ordered_amount": ordered_amount,
				"requested_amount": requested_amount,
				config["draft_amount_key"]: draft_amount,
				"remaining_before": remaining_before,
				"remaining_after": remaining_after,
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

import json

import frappe


def submit_quotation(rfq_name, supplier, items):
	"""Core supplier quotation submission logic. Caller is responsible for
	authorization (confirming the acting supplier is actually listed on this
	RFQ) — `supplier` must be passed explicitly here since a Request for
	Quotation can list multiple suppliers in its own `suppliers` child table,
	unlike Purchase Order/Purchase Invoice which each belong to exactly one
	supplier and can have it derived from the document itself."""
	if isinstance(items, str):
		items = json.loads(items)

	if not items or not isinstance(items, list):
		frappe.throw("At least one item is required.", frappe.ValidationError)

	for item in items:
		rate = float(item.get("rate") or 0)
		if rate <= 0:
			frappe.throw(
				f"Rate for item '{item.get('item_code', '')}' must be greater than zero.",
				frappe.ValidationError
			)

	# A supplier has no way to know or provide the buyer's internal warehouse,
	# but ERPNext requires one per stock item row on Supplier Quotation. Auto-fill
	# from the item's per-company default (same mechanism already proven in
	# proc_portal's New Request form) — invisible to the supplier, with a clear
	# error instead of ERPNext's raw validation message if no default exists.
	# Also used explicitly below as the new Supplier Quotation's own `company`
	# (not left to ERPNext's ambient default, which resolved to the wrong
	# company in live testing — same class of bug already fixed once before
	# in proc_portal's create_request()).
	company = frappe.db.get_value("Request for Quotation", rfq_name, "company")
	for item in items:
		if not item.get("warehouse"):
			default_warehouse = frappe.db.get_value(
				"Item Default", {"parent": item.get("item_code"), "company": company}, "default_warehouse"
			)
			if default_warehouse:
				item["warehouse"] = default_warehouse
			else:
				frappe.throw(
					f"Item {item.get('item_code')} has no default warehouse configured for {company}. "
					f"Please contact procurement to set one before this quotation can be submitted."
				)

	sq = frappe.get_doc({
		"doctype": "Supplier Quotation",
		"supplier": supplier,
		"company": company,
		"transaction_date": frappe.utils.today(),
		"items": []
	})

	for item in items:
		sq.append("items", {
			"item_code": item.get("item_code"),
			"qty": item.get("qty"),
			"rate": float(item.get("rate") or 0),
			"uom": item.get("uom"),
			"warehouse": item.get("warehouse"),
			"request_for_quotation": rfq_name,
			"request_for_quotation_item": item.get("name"),
			"lead_time_days": item.get("lead_time_days"),
			"expected_delivery_date": item.get("expected_delivery_date"),
		})

	sq.insert(ignore_permissions=True)
	# ERPNext's own quote_status sync (Request for Quotation Supplier ->
	# Received) only runs from Supplier Quotation's on_submit hook — leaving
	# this as a Draft would silently strand the RFQ's status tracking forever.
	# A supplier's quotation submission is final from their side, so submitting
	# here matches the real-world action, not just an editable draft.
	sq.submit()
	frappe.db.commit()
	return {"success": True, "quotation_name": sq.name}


def generate_comparison_sheet(rfq_name):
	"""Generates (or regenerates) an RFQ Comparison Sheet, scoring every
	supplier's quote against every other supplier who quoted the SAME item,
	per the formula confirmed 2026-08-24 (see PROC_APP_SPEC.md).
	Missing/zero lead_time_days scores 0 for that factor and is EXCLUDED
	from the "best lead time" reference calculation, so a supplier who
	didn't provide one can never accidentally win on that basis."""
	rfq = frappe.get_doc("Request for Quotation", rfq_name)
	price_weight = rfq.price_weight or 0
	lead_time_weight = rfq.lead_time_weight or 0

	quotes = frappe.db.sql("""
		SELECT sqi.item_code, sqi.rate, sqi.lead_time_days, sq.supplier, sq.name as sq_name, sqi.name as sqi_name
		FROM `tabSupplier Quotation Item` sqi
		JOIN `tabSupplier Quotation` sq ON sq.name = sqi.parent
		WHERE sqi.request_for_quotation = %s AND sq.docstatus = 1
	""", (rfq_name,), as_dict=True)

	by_item = {}
	for q in quotes:
		by_item.setdefault(q.item_code, []).append(q)

	rows = []
	for item_code, item_quotes in by_item.items():
		min_price = min(q.rate for q in item_quotes) if item_quotes else 0
		real_lead_times = [q.lead_time_days for q in item_quotes if q.lead_time_days and q.lead_time_days > 0]
		min_lead_time = min(real_lead_times) if real_lead_times else None

		ranked = []
		for q in item_quotes:
			price_score = (min_price / q.rate * 100) if q.rate else 0
			if q.lead_time_days and q.lead_time_days > 0 and min_lead_time:
				lead_time_score = min_lead_time / q.lead_time_days * 100
			else:
				lead_time_score = 0
			weighted_mark = (price_score * price_weight / 100) + (lead_time_score * lead_time_weight / 100)
			ranked.append({
				"item_code": item_code,
				"supplier": q.supplier,
				"quoted_price": q.rate,
				"lead_time_days": q.lead_time_days or 0,
				"price_score": round(price_score, 2),
				"lead_time_score": round(lead_time_score, 2),
				"weighted_mark": round(weighted_mark, 2),
				"supplier_quotation": q.sq_name,
				"supplier_quotation_item": q.sqi_name,
			})
		ranked.sort(key=lambda r: r["weighted_mark"], reverse=True)
		for i, r in enumerate(ranked, start=1):
			r["item_rank"] = i
		rows.extend(ranked)

	existing = frappe.db.get_value("RFQ Comparison Sheet", {"request_for_quotation": rfq_name}, "name")
	if existing:
		frappe.delete_doc("RFQ Comparison Sheet", existing, force=True, ignore_permissions=True)

	sheet = frappe.get_doc({
		"doctype": "RFQ Comparison Sheet",
		"request_for_quotation": rfq_name,
		"price_weight": price_weight,
		"lead_time_weight": lead_time_weight,
		"items": rows,
	})
	sheet.insert(ignore_permissions=True)
	frappe.db.commit()
	return sheet.name

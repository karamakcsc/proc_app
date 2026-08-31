frappe.provide('proc_app.rfq_comparison');

frappe.pages['rfq-comparison'].on_page_load = function (wrapper) {
	var page = frappe.ui.make_app_page({
		parent: wrapper,
		title: __('RFQ Comparison'),
		single_column: true,
	});
	proc_app.rfq_comparison.wrapper = wrapper;
	proc_app.rfq_comparison.page = page;
	load_and_render();
};

frappe.pages['rfq-comparison'].refresh = function () {
	// refresh fires on every re-visit (route may now point at a different
	// sheet) -- frappe.require() is a cheap no-op for already-loaded assets
	// (AssetManager tracks _executed by path), so re-running it here is safe.
	load_and_render();
};

function esc(v) {
	return frappe.utils.escape_html(v === null || v === undefined ? '' : String(v));
}

// A JS-string literal (JSON.stringify output) embedded inside a
// double-quoted HTML attribute (x-data="...(js_attr(x))...") needs its own
// double quotes HTML-escaped, or the first one prematurely closes the
// attribute and everything after it becomes stray markup -- confirmed as a
// real bug via a jsdom+Alpine runtime test (Alpine's own parser reported
// "Unexpected token '}'" on a silently truncated expression) before this
// helper existed; every x-data/@click/@change argument goes through it now.
function js_attr(v) {
	return esc(JSON.stringify(v));
}

function load_and_render() {
	frappe.require([
		'/assets/proc_portal/css/portal.css',
		'/assets/proc_app/css/rfq_comparison_page.css',
		'https://cdn.jsdelivr.net/npm/alpinejs@3.x.x/dist/cdn.min.js',
	]).then(render);
}

function render() {
	var page = proc_app.rfq_comparison.page;
	var container = page.main;
	var el = container.get(0);

	// Tear down any previously-initialised Alpine subtree before replacing the
	// markup. Alpine's own MutationObserver would eventually notice the removal
	// on its own, but calling destroyTree explicitly is the documented,
	// deterministic way to do it rather than relying on async observer timing
	// (confirmed present in the real alpinejs@3.17.1 CDN bundle -- fetched and
	// grepped directly, not assumed: window.Alpine.destroyTree / initTree).
	if (window.Alpine && el.dataset.alpineInitialised) {
		window.Alpine.destroyTree(el);
	}

	var sheet_name = frappe.get_route()[1];
	if (!sheet_name) {
		container.html(
			'<div class="rfq-comparison-page"><div class="portal-card">' +
			__('Open this page from an RFQ or Comparison Sheet\'s "View Comparison Sheet" / "By Proposal Comparison" button — no sheet specified in the route.') +
			'</div></div>'
		);
		delete el.dataset.alpineInitialised;
		return;
	}

	container.html('<div class="rfq-comparison-page"><p style="color:var(--portal-text-muted, #6B7280);">' + __('Loading...') + '</p></div>');

	frappe.db.get_value('RFQ Comparison Sheet', sheet_name, 'request_for_quotation').then(function (r) {
		var rfq_name = r.message && r.message.request_for_quotation;
		if (!rfq_name) {
			container.html('<div class="rfq-comparison-page"><div class="portal-card">' + __('Comparison sheet {0} not found.', [esc(sheet_name)]) + '</div></div>');
			return;
		}

		page.set_title(__('RFQ Comparison') + ' — ' + sheet_name);

		Promise.all([
			frappe.call({ method: 'proc_portal.api.rfqs.get_comparison_sheet', args: { rfq_name: rfq_name } }),
			frappe.call({ method: 'proc_portal.api.rfqs.get_purchase_orders_for_rfq', args: { rfq_name: rfq_name } }),
			frappe.call({ method: 'proc_portal.api.rfqs.get_comparison_sheet_actions', args: { sheet_name: sheet_name } }),
		]).then(function (results) {
			var comparison = results[0].message;
			var purchase_orders = results[1].message || [];
			var sheet_actions = results[2].message || [];

			if (!comparison) {
				container.html('<div class="rfq-comparison-page"><div class="portal-card">' + __('No comparison data.') + '</div></div>');
				return;
			}

			container.html(build_page_html(rfq_name, comparison, purchase_orders, sheet_actions));

			var fresh_el = container.get(0);
			fresh_el.dataset.alpineInitialised = '1';
			if (window.Alpine) {
				window.Alpine.initTree(fresh_el);
			}

			container.find('.rfq-back-to-rfq').on('click', function (e) {
				e.preventDefault();
				frappe.set_route('Form', 'Request for Quotation', rfq_name);
			});
		});
	});
}

function build_page_html(rfq_name, comparison, purchase_orders, sheet_actions) {
	var status_color = comparison.workflow_state === 'Approved' ? 'var(--portal-success)'
		: comparison.workflow_state === 'Rejected' ? 'var(--portal-danger)'
		: comparison.workflow_state === 'Pending Approval' ? 'var(--portal-warning)'
		: 'var(--text-secondary)';

	var has_existing_pos = purchase_orders.length > 0;

	var html = '<div class="rfq-comparison-page">';
	html += '<h1>' + __('Quotation Comparison') + ' — ' + esc(rfq_name) + '</h1>';
	html += '<p style="color:var(--portal-text-muted); margin-bottom:20px;">'
		+ __('Weighting: Price {0}% · Lead Time {1}%', [esc(comparison.price_weight), esc(comparison.lead_time_weight)])
		+ '</p>';

	if (comparison.selection_finalized_by) {
		html += '<p style="color:var(--portal-text-muted); font-size:13px; margin-bottom:20px;">'
			+ __('Selections last updated by {0} on {1}.', [esc(comparison.selection_finalized_by), esc(comparison.selection_finalized_on)])
			+ '</p>';
	}

	html += build_actions_bar(rfq_name, comparison, sheet_actions, status_color, has_existing_pos);
	html += build_mode_toggle_section(comparison);
	html += build_po_section(purchase_orders);

	html += '<a href="#" class="rfq-back-to-rfq portal-btn" style="background:white; color:var(--portal-primary-dark); border:1px solid var(--portal-primary);">'
		+ __('← Back to RFQ') + '</a>';
	html += '</div>';
	return html;
}

function build_actions_bar(rfq_name, comparison, sheet_actions, status_color, has_existing_pos) {
	var html = '<div x-data="proc_app_poGenActions(' + js_attr(rfq_name) + ', ' + (has_existing_pos ? 'true' : 'false') + ')">';
	html += '<div x-show="error" style="color:var(--portal-danger); margin-bottom:12px;" x-text="error"></div>';
	html += '<div x-show="success" style="color:var(--portal-success); margin-bottom:12px;" x-text="success"></div>';

	html += '<p style="margin-bottom:12px;">' + __('Status') + ': <span style="font-weight:600; color:' + status_color + ';">'
		+ esc(comparison.workflow_state || 'Draft') + '</span></p>';

	if (sheet_actions.length) {
		html += '<div style="margin-bottom:20px;">';
		sheet_actions.forEach(function (action) {
			var is_reject = action.indexOf('Reject') !== -1;
			html += '<button class="portal-btn ' + (is_reject ? 'portal-btn-danger' : 'portal-btn-sky') + '" '
				+ '@click="doSheetAction(' + js_attr(action) + ')" :disabled="loading" style="margin-right:8px;">'
				+ esc(action) + '</button>';
		});
		html += '</div>';
	}

	html += '<a x-show="hasExistingPOs" href="#linked-purchase-orders" class="portal-btn portal-btn-sky" style="margin-bottom:20px;">' + __('View Purchase Orders') + '</a>';
	if (comparison.workflow_state === 'Approved') {
		html += '<button x-show="!hasExistingPOs" class="portal-btn portal-btn-sky" @click="generate()" :disabled="loading" style="margin-bottom:20px;">'
			+ '<span x-show="!loading">' + __('Generate Purchase Orders') + '</span>'
			+ '<span x-show="loading">' + __('Generating...') + '</span></button>';
	} else {
		html += '<p x-show="!hasExistingPOs" style="color:var(--portal-text-muted); font-size:13px; margin-bottom:20px;">'
			+ __('Purchase orders can only be generated once this comparison sheet is Approved. Current status: {0}', ['<strong>' + esc(comparison.workflow_state || 'Draft') + '</strong>'])
			+ '</p>';
	}
	html += '</div>';
	return html;
}

function build_mode_toggle_section(comparison) {
	var html = '<div x-data="proc_app_comparisonActions(' + js_attr(comparison.sheet_name) + ')">';

	html += '<label style="position:relative; display:inline-flex; align-items:center; cursor:pointer; gap:10px; margin-bottom:20px;">'
		+ '<span style="font-size:13px; font-weight:500;" :style="{ color: mode === \'item\' ? \'var(--kcsc-sky-text)\' : \'var(--text-muted)\' }">' + __('By Item') + '</span>'
		+ '<div @click="mode = mode === \'item\' ? \'proposal\' : \'item\'" style="width:44px; height:24px; border-radius:12px; position:relative; transition:background 0.2s;" :style="{ background: mode === \'proposal\' ? \'var(--kcsc-sky)\' : \'var(--border-hairline)\' }">'
		+ '<div style="width:20px; height:20px; border-radius:50%; background:white; position:absolute; top:2px; transition:left 0.2s; box-shadow:0 1px 3px rgba(0,0,0,0.2);" :style="{ left: mode === \'proposal\' ? \'22px\' : \'2px\' }"></div>'
		+ '</div>'
		+ '<span style="font-size:13px; font-weight:500;" :style="{ color: mode === \'proposal\' ? \'var(--kcsc-sky-text)\' : \'var(--text-muted)\' }">' + __('By Proposal') + '</span>'
		+ '</label>';

	html += '<div x-show="mode === \'proposal\'">' + build_proposal_table(comparison) + '</div>';
	html += '<div x-show="mode === \'item\'">' + build_item_summary_table(comparison) + build_item_detail_tables(comparison) + '</div>';

	html += '</div>';
	return html;
}

function build_proposal_table(comparison) {
	var html = '<h2>' + __('Summary — Overall Ranking by Proposal') + '</h2>';
	html += '<div class="portal-card" style="padding:0; overflow:hidden; margin-bottom:24px;"><table style="width:100%; border-collapse:collapse;">';
	html += '<thead><tr style="background:var(--portal-bg); text-align:left; font-size:12px; color:var(--portal-text-muted);">'
		+ ['Rank', 'Supplier', 'Items Quoted', 'Avg Price Score', 'Avg Lead Time Score', 'Average Weighted Mark', 'Status', 'Select']
			.map(function (h) { return '<th style="padding:12px 16px;">' + __(h) + '</th>'; }).join('')
		+ '</tr></thead><tbody>';

	(comparison.by_proposal || []).forEach(function (row) {
		var row_style = 'border-top:1px solid var(--portal-border); ';
		if (row.is_proposal_selected) row_style += 'border-left:3px solid var(--portal-success); ';
		if (!row.eligible) row_style += 'background:var(--bg-warning); ';
		else if (row.rank === 1) row_style += 'background:#EEF0FD; font-weight:600; ';

		html += '<tr style="' + row_style + '">';
		html += '<td style="padding:12px 16px;">' + (row.eligible ? (esc(row.rank) + (row.rank === 1 ? ' 🏆' : '')) : '—') + '</td>';
		html += '<td style="padding:12px 16px;">' + esc(row.supplier)
			+ (row.eligible && row.rank === 1 ? ' <span style="font-weight:600;">(' + __('Overall Winner') + ')</span>' : '')
			+ (row.is_proposal_selected ? ' <span style="color:var(--portal-success); font-weight:600;">✓ ' + __('Selected') + '</span>' : '')
			+ '</td>';
		html += '<td style="padding:12px 16px;">' + esc(row.items_quoted) + ' / ' + esc(comparison.total_item_count) + '</td>';
		html += '<td style="padding:12px 16px;">' + esc(Number(row.average_price_score || 0).toFixed(2)) + '</td>';
		html += '<td style="padding:12px 16px;">' + esc(Number(row.average_lead_time_score || 0).toFixed(2)) + '</td>';
		html += '<td style="padding:12px 16px;">' + esc(Number(row.average_mark || 0).toFixed(2)) + '</td>';
		html += '<td style="padding:12px 16px;">' + (row.eligible
			? '<span style="color:var(--portal-success);">' + __('Complete') + '</span>'
			: '<span style="color:var(--portal-warning); font-weight:500;">' + __('Incomplete — missing {0} of {1} items', [esc(row.items_missing), esc(comparison.total_item_count)]) + '</span>') + '</td>';
		html += '<td style="padding:12px 16px;">' + (row.eligible
			? '<button type="button" @click="selectProposal(' + js_attr(row.supplier) + ', ' + row.rank + ')" :disabled="selectionLoading" class="portal-btn ' + (row.is_proposal_selected ? 'portal-btn-sky' : '') + '" style="padding:6px 14px; font-size:12px; margin-bottom:0;">'
				+ (row.is_proposal_selected ? __('Selected') : __('Select')) + '</button>'
			: '<span style="color:var(--text-secondary); font-size:12px;">' + __('Not eligible') + '</span>') + '</td>';
		html += '</tr>';
	});

	html += '</tbody></table></div>';
	return html;
}

function build_item_summary_table(comparison) {
	var html = '<h2>' + __('Summary — Winning Supplier by Item') + '</h2>';
	html += '<div class="portal-card" style="padding:0; overflow:hidden; margin-bottom:24px;"><table style="width:100%; border-collapse:collapse;">';
	html += '<thead><tr style="background:var(--portal-bg); text-align:left; font-size:12px; color:var(--portal-text-muted);">'
		+ ['Item', 'Item Name', 'Selected Supplier', 'Weighted Mark'].map(function (h) { return '<th style="padding:12px 16px;">' + __(h) + '</th>'; }).join('')
		+ '</tr></thead><tbody>';

	Object.keys(comparison.by_item || {}).forEach(function (item_code) {
		var rows = comparison.by_item[item_code];
		var winner = rows.filter(function (r) { return r.item_rank === 1; })[0];
		var selected = rows.filter(function (r) { return r.is_selected; })[0];
		var display_row = selected || winner;

		html += '<tr style="border-top:1px solid var(--portal-border);">';
		html += '<td style="padding:12px 16px;">' + esc(item_code) + '</td>';
		html += '<td style="padding:12px 16px; color:var(--portal-text-muted);">' + esc(winner ? (winner.item_name || '—') : '—') + '</td>';
		html += '<td style="padding:12px 16px; font-weight:600;">' + esc(display_row.supplier) + (display_row.item_rank === 1 ? ' 🏆' : '');
		if (selected && selected.item_rank !== 1) {
			html += '<span style="color:var(--portal-warning); font-size:11px; margin-left:4px; font-weight:500;">(' + __('override') + ')</span>'
				+ '<div style="font-size:11px; color:var(--text-secondary); font-weight:400; margin-top:2px;">🏆 ' + __('Recommended: {0}', [esc(winner.supplier)]) + '</div>';
		}
		html += '</td>';
		html += '<td style="padding:12px 16px;">' + esc(display_row.weighted_mark) + '</td>';
		html += '</tr>';
	});

	html += '</tbody></table></div>';
	return html;
}

function build_item_detail_tables(comparison) {
	var html = '';
	Object.keys(comparison.by_item || {}).forEach(function (item_code) {
		var rows = comparison.by_item[item_code];
		var item_display_name = rows[0].item_name;
		var item_display_uom = rows[0].uom;

		html += '<h2>' + esc(item_code) + (item_display_name ? ' — ' + esc(item_display_name) : '') + (item_display_uom ? ' (' + esc(item_display_uom) + ')' : '') + '</h2>';
		html += '<div class="portal-card" style="padding:0; overflow:hidden; margin-bottom:20px;"><table style="width:100%; border-collapse:collapse;">';
		html += '<thead><tr style="background:var(--portal-bg); text-align:left; font-size:12px; color:var(--portal-text-muted);">'
			+ ['Rank', 'Supplier', 'Price', 'Lead Time (days)', 'Price Score', 'Lead Time Score', 'Weighted Mark', 'Select']
				.map(function (h) { return '<th style="padding:12px 16px;">' + __(h) + '</th>'; }).join('')
			+ '</tr></thead><tbody>';

		rows.forEach(function (row) {
			var row_style = 'border-top:1px solid var(--portal-border); ';
			if (row.is_selected) row_style += 'border-left:3px solid var(--portal-success); ';
			if (row.item_rank === 1) row_style += 'background:#EEF0FD; font-weight:600; ';

			html += '<tr style="' + row_style + '">';
			html += '<td style="padding:12px 16px;">' + esc(row.item_rank) + (row.item_rank === 1 ? ' 🏆' : '') + '</td>';
			html += '<td style="padding:12px 16px;">' + esc(row.supplier) + '</td>';
			html += '<td style="padding:12px 16px;">' + esc(row.quoted_price) + '</td>';
			html += '<td style="padding:12px 16px;">' + esc(row.lead_time_days) + '</td>';
			html += '<td style="padding:12px 16px;">' + esc(row.price_score) + '</td>';
			html += '<td style="padding:12px 16px;">' + esc(row.lead_time_score) + '</td>';
			html += '<td style="padding:12px 16px;">' + esc(row.weighted_mark) + '</td>';
			html += '<td style="padding:12px 16px;">'
				+ '<label style="display:flex; align-items:center; gap:6px; cursor:pointer; font-weight:400; margin:0;">'
				+ '<input type="radio" name="select_' + esc(item_code) + '" ' + (row.is_selected ? 'checked' : '')
				+ ' @change="selectItem(' + js_attr(row.name) + ', ' + row.item_rank + ')" :disabled="selectionLoading">'
				+ (row.is_selected ? '<span style="color:var(--portal-success); font-weight:600; font-size:12px;">✓ ' + __('Selected') + '</span>' : '')
				+ '</label>';
			if (row.is_manual_override) {
				html += '<div style="margin-top:4px; font-size:11px; color:var(--portal-warning); font-weight:500;" title="' + esc(row.selection_reason || '') + '">'
					+ '⚠ ' + __('Manual override') + (row.selection_reason ? ': ' + esc(row.selection_reason) : '') + '</div>';
			}
			html += '</td></tr>';
		});

		html += '</tbody></table></div>';
	});
	return html;
}

function build_po_section(purchase_orders) {
	var html = '<div class="rich-section" id="linked-purchase-orders"><p class="rich-section-label">' + __('Linked Purchase Orders') + '</p>';
	if (purchase_orders.length) {
		html += '<div class="rich-card" style="border-radius:8px;">';
		purchase_orders.forEach(function (po) {
			html += '<div class="rich-item-row rfq-po-link" data-po-name="' + esc(po.name) + '">'
				+ '<a href="#" style="color:var(--kcsc-sky-text); font-weight:500; text-decoration:none;">' + esc(po.name) + '</a>'
				+ '<div style="font-size:13px; color:var(--text-secondary);">' + esc(po.supplier) + ' · ' + esc(po.status) + '</div>'
				+ '</div>';
		});
		html += '</div>';
	} else {
		html += '<p style="font-size:14px; color:var(--text-secondary);">' + __('No purchase orders linked.') + '</p>';
	}
	html += '</div>';
	return html;
}

$(document).on('click', '.rfq-po-link', function (e) {
	e.preventDefault();
	var po_name = $(this).attr('data-po-name');
	if (po_name) frappe.set_route('Form', 'Purchase Order', po_name);
});

// Alpine components -- ported near-verbatim from proc_portal's
// rfq-comparison.html (poGenActions()/comparisonActions()), which already
// call the exact same whitelisted endpoints. Two deliberate adaptations for
// the desk context, not changes to the business logic itself:
//   1. frappe.call() instead of raw fetch()+manual CSRF header/error-message
//      parsing -- desk's own call wrapper already handles both natively.
//   2. A scoped re-render (render()) instead of window.location.reload()
//      after a successful action -- a full page reload would reload the
//      entire desk SPA, not just this page.
window.proc_app_poGenActions = function (rfq_name, initial_has_pos) {
	return {
		loading: false, error: '', success: '',
		hasExistingPOs: !!initial_has_pos,
		generate() {
			this.loading = true;
			this.error = ''; this.success = '';
			frappe.call({ method: 'proc_portal.api.rfqs.trigger_po_generation', args: { rfq_name: rfq_name } })
				.then((r) => {
					this.loading = false;
					if (!r.message) { this.error = __('Failed to generate purchase orders.'); return; }
					this.success = __('Created: {0}', [r.message.purchase_orders.join(', ')]);
					this.hasExistingPOs = true;
					render();
				})
				.catch(() => { this.loading = false; this.error = __('Something went wrong.'); });
		},
		doSheetAction(action) {
			this.loading = true;
			this.error = ''; this.success = '';
			frappe.call({ method: 'proc_portal.api.rfqs.do_comparison_sheet_action', args: { sheet_name: frappe.get_route()[1], action: action } })
				.then((r) => {
					this.loading = false;
					if (!r.message) { this.error = __('Action failed.'); return; }
					render();
				})
				.catch(() => { this.loading = false; this.error = __('Something went wrong.'); });
		},
	};
};

window.proc_app_comparisonActions = function (sheet_name) {
	return {
		mode: 'item',
		selectionLoading: false,
		selectItem(row_name, item_rank) {
			var reason = null;
			if (item_rank !== 1) {
				reason = window.prompt(__('Please explain why you are selecting a supplier other than the highest-scoring one:'));
				if (reason === null) return;
				if (!reason.trim()) { frappe.msgprint(__('A justification is required to select a supplier other than the highest-scoring one.')); return; }
			}
			this.selectionLoading = true;
			frappe.call({ method: 'proc_portal.api.rfqs.set_item_selection', args: { sheet_name: sheet_name, row_name: row_name, reason: reason } })
				.then((r) => {
					this.selectionLoading = false;
					if (!r.message) frappe.msgprint(__('Failed to update selection.'));
					render();
				})
				.catch(() => { this.selectionLoading = false; frappe.msgprint(__('Something went wrong.')); });
		},
		selectProposal(supplier, rank) {
			var reason = null;
			if (rank !== 1) {
				reason = window.prompt(__('Please explain why you are selecting a proposal other than the highest-scoring one:'));
				if (reason === null) return;
				if (!reason.trim()) { frappe.msgprint(__('A justification is required to select a proposal other than the highest-scoring one.')); return; }
			}
			this.selectionLoading = true;
			frappe.call({ method: 'proc_portal.api.rfqs.select_entire_proposal', args: { sheet_name: sheet_name, supplier: supplier, reason: reason } })
				.then((r) => {
					this.selectionLoading = false;
					if (!r.message) frappe.msgprint(__('Failed to update selection.'));
					render();
				})
				.catch(() => { this.selectionLoading = false; frappe.msgprint(__('Something went wrong.')); });
		},
	};
};

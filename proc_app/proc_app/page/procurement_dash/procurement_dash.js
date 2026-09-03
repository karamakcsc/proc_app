frappe.provide('proc_app.procurement_dashboard');

frappe.pages['procurement-dash'].on_page_load = function (wrapper) {
	var page = frappe.ui.make_app_page({
		parent: wrapper,
		title: __('Procurement Dashboard'),
		single_column: true,
	});
	proc_app.procurement_dashboard.wrapper = wrapper;
	proc_app.procurement_dashboard.page = page;
	proc_app.procurement_dashboard.charts = [];
	load_and_render();
};

frappe.pages['procurement-dash'].refresh = function () {
	// refresh fires on every re-visit -- frappe.require() is a cheap no-op
	// for already-loaded assets (AssetManager tracks _executed by path), so
	// re-running it here is safe.
	load_and_render();
};

function esc(v) {
	return frappe.utils.escape_html(v === null || v === undefined ? '' : String(v));
}

function load_and_render() {
	frappe.require([
		'/assets/proc_portal/css/portal.css',
		'/assets/proc_app/css/procurement_dash_page.css',
		'https://cdn.jsdelivr.net/npm/alpinejs@3.x.x/dist/cdn.min.js',
		'https://cdnjs.cloudflare.com/ajax/libs/Chart.js/4.4.0/chart.umd.min.js',
	]).then(render);
}

function render() {
	var page = proc_app.procurement_dashboard.page;
	var container = page.main;
	var el = container.get(0);

	// Destroy every Chart.js instance from the PRIOR render before the DOM
	// gets replaced. This must happen here, not via a Chart.getChart(id)
	// lookup after container.html() runs -- by then the old canvas element
	// is already gone, replaced by a brand-new, chart-less one with the same
	// id, so Chart.getChart(id) would silently find nothing to destroy and
	// the old instance leaks. The portal's own port of this same code never
	// hit this: a full page navigation there discards the whole JS context,
	// so the leak was never observable. Desk's refresh() re-runs render() in
	// the same persistent context on every revisit, so here it's a real,
	// growing leak, not a hypothetical one -- destroying by stored instance
	// reference (not by re-resolving the element) is the actual fix, applied
	// the same way rfq_comparison.js already destroys the old Alpine tree
	// before replacing the DOM, just one step earlier for Chart.js's own
	// registry.
	(proc_app.procurement_dashboard.charts || []).forEach(function (chart) {
		chart.destroy();
	});
	proc_app.procurement_dashboard.charts = [];

	if (window.Alpine && el.dataset.alpineInitialised) {
		window.Alpine.destroyTree(el);
	}

	container.html(build_page_html());

	var fresh_el = container.get(0);
	fresh_el.dataset.alpineInitialised = '1';
	if (window.Alpine) {
		window.Alpine.initTree(fresh_el);
	}
}

function register_chart(chart) {
	proc_app.procurement_dashboard.charts.push(chart);
	return chart;
}

function build_page_html() {
	var html = '<div class="procurement-dashboard-page">';
	html += '<h1>' + __('Procurement Dashboard') + '</h1>';
	// No x-init="init()" here, deliberately -- Alpine's own x-data directive
	// handler already auto-calls any init() method the data object defines
	// (confirmed directly in the real alpinejs@3.17.1 bundle's own source:
	// `t.hasOwnProperty("init") && typeof t.init === "function" && data.init()`
	// runs as part of processing x-data itself). Adding an explicit
	// x-init="init()" on top of that -- the pattern the portal's own
	// dashboard.html actually uses -- calls init() a SECOND time, fetching
	// every dashboard API twice and creating every chart twice per page
	// load. In the portal this silently "self-heals" via its own
	// Chart.getChart(id)-before-create guards (the second pass destroys and
	// replaces the first pass's charts on the same still-live canvases), so
	// it was never visibly broken there -- just a wasted double round-trip.
	// Confirmed via a minimal, isolated jsdom+Alpine repro before concluding
	// this, not assumed from the dashboard's own complexity.
	html += '<div x-data="proc_app_dashboardPage()">';

	html += '<div x-show="loading" style="color:var(--text-muted); padding:20px;">' + __('Loading...') + '</div>';

	// Exact drill-down filters for each card, matching get_dashboard_summary()'s
	// own query criteria field-for-field (see PROC_APP_SPEC.md for the
	// verification that each drill-down's count matches its card). Dates are
	// computed once, here, via the same frappe.datetime utilities the desk
	// list-view filter bar itself would produce.
	var this_month_start = frappe.datetime.get_today().slice(0, 8) + '01';
	var today = frappe.datetime.get_today();
	var today_plus_30 = frappe.datetime.add_days(today, 30);

	html += '<div x-show="!loading" class="dashboard-stat-grid">';
	html += stat_card('var(--kcsc-sky)', 'summary.open_material_requests', __('Open Requests'),
		'M19.5 14.25v-2.625a3.375 3.375 0 00-3.375-3.375h-1.5A1.125 1.125 0 0113.5 7.125v-1.5a3.375 3.375 0 00-3.375-3.375H8.25m0 12.75h7.5m-7.5 3H12M10.5 2.25H5.625c-.621 0-1.125.504-1.125 1.125v17.25c0 .621.504 1.125 1.125 1.125h12.75c.621 0 1.125-.504 1.125-1.125V11.25a9 9 0 00-9-9z',
		{ doctype: 'Material Request', filters: { docstatus: ['!=', 2], workflow_state: ['not in', ['Approved - Issue', 'Approved - Purchase', 'Rejected', 'Forwarded to Purchase']] } });
	html += stat_card('var(--kcsc-indigo)', 'summary.active_rfqs', __('Active RFQs'),
		'M8.625 12a.375.375 0 11-.75 0 .375.375 0 01.75 0zm0 0H8.25m4.125 0a.375.375 0 11-.75 0 .375.375 0 01.75 0zm0 0H12m4.125 0a.375.375 0 11-.75 0 .375.375 0 01.75 0zm0 0h-.375M21 12c0 4.556-4.03 8.25-9 8.25a9.764 9.764 0 01-2.555-.337A5.972 5.972 0 015.41 20.97a5.969 5.969 0 01-.474-.065 4.48 4.48 0 00.978-2.025c.09-.457-.133-.901-.467-1.226C3.93 16.178 3 14.189 3 12c0-4.556 4.03-8.25 9-8.25s9 3.694 9 8.25z',
		{ doctype: 'Request for Quotation', filters: { workflow_state: 'Approved', docstatus: 1 } });

	html += '<div class="dashboard-stat-card-link"' + build_drilldown_attr({ doctype: 'Purchase Order', filters: { docstatus: 1, transaction_date: ['>=', this_month_start] } })
		+ ' style="background:var(--kcsc-green); border-radius:12px; padding:1.1rem; display:flex; align-items:center; justify-content:space-between; color:white;">'
		+ '<div>'
		+ '<p style="font-size:26px; font-weight:700; margin:0;" x-text="summary.pos_this_month_count"></p>'
		+ '<p style="font-size:11px; margin:4px 0 0; text-transform:uppercase; letter-spacing:0.04em; opacity:0.9;">' + __('POs This Month') + '</p>'
		+ '<p style="font-size:11px; margin:2px 0 0; opacity:0.85;" x-text="\'$\' + Number(summary.pos_this_month_total).toLocaleString()"></p>'
		+ '</div>' + stat_icon('M2.25 3h1.386c.51 0 .955.343 1.087.835l.383 1.437M7.5 14.25a3 3 0 00-3 3h15.75m-12.75-3h11.218c1.121-2.3 2.1-4.684 2.924-7.138a60.114 60.114 0 00-16.536-1.84M7.5 14.25L5.106 5.272M6 20.25a.75.75 0 11-1.5 0 .75.75 0 011.5 0zm12.75 0a.75.75 0 11-1.5 0 .75.75 0 011.5 0z') + '</div>';

	html += stat_card('var(--kcsc-amber)', 'summary.contracts_expiring_soon', __('Contracts Expiring'),
		'M6.75 3v2.25M17.25 3v2.25M3 18.75V7.5a2.25 2.25 0 012.25-2.25h13.5A2.25 2.25 0 0121 7.5v11.25m-18 0A2.25 2.25 0 005.25 21h13.5A2.25 2.25 0 0021 18.75m-18 0v-7.5A2.25 2.25 0 015.25 9h13.5A2.25 2.25 0 0121 11.25v7.5',
		{ doctype: 'Contract', filters: { status: 'Active', end_date: [['>=', today], ['<=', today_plus_30]] } });
	html += stat_card('var(--kcsc-amber)', 'summary.unbilled_pos', __('Unbilled POs'),
		'M2.25 3h1.386c.51 0 .955.343 1.087.835l.383 1.437M7.5 14.25a3 3 0 00-3 3h15.75m-12.75-3h11.218c1.121-2.3 2.1-4.684 2.924-7.138a60.114 60.114 0 00-16.536-1.84M7.5 14.25L5.106 5.272M6 20.25a.75.75 0 11-1.5 0 .75.75 0 011.5 0zm12.75 0a.75.75 0 11-1.5 0 .75.75 0 011.5 0z',
		{ doctype: 'Purchase Order', filters: { docstatus: 1, per_billed: ['<', 100] } });
	html += stat_card('var(--portal-danger)', 'summary.invoices_awaiting_payment', __('Awaiting Payment'),
		'M12 7.5h1.5m-1.5 3h1.5m-7.5 3h7.5m-7.5 3h7.5m3-9h3.375c.621 0 1.125.504 1.125 1.125V18a2.25 2.25 0 01-2.25 2.25M16.5 7.5V18a2.25 2.25 0 002.25 2.25M16.5 7.5V4.875c0-.621-.504-1.125-1.125-1.125H4.125C3.504 3.75 3 4.254 3 4.875V18a2.25 2.25 0 002.25 2.25h13.5M6 7.5h3v3H6v-3z',
		{ doctype: 'Purchase Invoice', filters: { docstatus: 1, outstanding_amount: ['>', 0] } });
	html += '</div>';

	html += '<div x-show="!loading" class="dashboard-chart-grid">';
	html += chart_card(__('Requests by Status'), 'statusLegend', 'statusChart');
	html += chart_card(__('Spending by Month'), 'monthLegend', 'monthChart');
	html += chart_card(__('Spending by Supplier'), 'supplierLegend', 'supplierChart');
	html += chart_card(__('RFQ Response Status'), 'rfqLegend', 'rfqChart');
	html += chart_card(__('Procurement Funnel'), 'funnelLegend', 'funnelChart');
	html += chart_card(__('PO Fulfillment Status'), 'fulfillmentLegend', 'fulfillmentChart');
	html += chart_card(__('Contract Expiry Timeline'), 'contractExpiryLegend', 'contractExpiryChart');
	html += chart_card(__('Invoice Aging'), 'invoiceAgingLegend', 'invoiceAgingChart');
	html += '</div>';

	html += '<h2 style="font-size:16px; margin:28px 0 12px;">' + __('Contract Portfolio') + '</h2>';

	html += '<div x-show="!loading" class="dashboard-stat-grid">';
	html += '<div style="background:var(--kcsc-sky); border-radius:12px; padding:1.1rem; display:flex; align-items:center; justify-content:space-between; color:white;">'
		+ '<div>'
		+ '<p style="font-size:26px; font-weight:700; margin:0;" x-text="\'$\' + Number(portfolio.total_active_value || 0).toLocaleString()"></p>'
		+ '<p style="font-size:11px; margin:4px 0 0; text-transform:uppercase; letter-spacing:0.04em; opacity:0.9;">' + __('Total Active Contract Value') + '</p>'
		+ '</div>' + stat_icon('M2.25 18.75a60.07 60.07 0 0115.797 2.101c.727.198 1.453-.342 1.453-1.096V18.75M3.75 4.5v.75A.75.75 0 013 6h-.75m0 0v-.375c0-.621.504-1.125 1.125-1.125H20.25M2.25 6v9m18-10.5v.75c0 .414.336.75.75.75h.75m-1.5-1.5h.375c.621 0 1.125.504 1.125 1.125v9.75c0 .621-.504 1.125-1.125 1.125h-.375m1.5-1.5H21a.75.75 0 00-.75.75v.75m0 0H3.75m0 0h-.375a1.125 1.125 0 01-1.125-1.125V15m1.5 1.5v-.75A.75.75 0 003 15h-.75M15 10.5a3 3 0 11-6 0 3 3 0 016 0zM21 12a.75.75 0 11-1.5 0 .75.75 0 011.5 0zM3.75 12a.75.75 0 11-1.5 0 .75.75 0 011.5 0z') + '</div>';
	html += stat_card('var(--kcsc-indigo)', 'activeContractsCount', __('Active Contracts'),
		'M9 12.75L11.25 15 15 9.75M21 12c0 1.268-.63 2.39-1.593 3.068a3.745 3.745 0 01-1.043 3.296 3.745 3.745 0 01-3.296 1.043A3.745 3.745 0 0112 21c-1.268 0-2.39-.63-3.068-1.593a3.746 3.746 0 01-3.296-1.043 3.745 3.745 0 01-1.043-3.296A3.745 3.745 0 013 12c0-1.268.63-2.39 1.593-3.068a3.745 3.745 0 011.043-3.296 3.746 3.746 0 013.296-1.043A3.745 3.745 0 0112 3c1.268 0 2.39.63 3.068 1.593a3.746 3.746 0 013.296 1.043 3.746 3.746 0 011.043 3.296A3.745 3.745 0 0121 12z');
	html += '<div style="background:var(--kcsc-amber); border-radius:12px; padding:1.1rem; display:flex; align-items:center; justify-content:space-between; color:white;">'
		+ '<div>'
		+ '<p style="font-size:26px; font-weight:700; margin:0;" x-text="portfolio.expiring_90 || 0"></p>'
		+ '<p style="font-size:11px; margin:4px 0 0; text-transform:uppercase; letter-spacing:0.04em; opacity:0.9;">' + __('Expiring in 90 Days') + '</p>'
		+ '</div>' + stat_icon('M6.75 3v2.25M17.25 3v2.25M3 18.75V7.5a2.25 2.25 0 012.25-2.25h13.5A2.25 2.25 0 0121 7.5v11.25m-18 0A2.25 2.25 0 005.25 21h13.5A2.25 2.25 0 0021 18.75m-18 0v-7.5A2.25 2.25 0 015.25 9h13.5A2.25 2.25 0 0121 11.25v7.5') + '</div>';
	html += '</div>';

	html += '<div x-show="!loading" class="dashboard-chart-grid">';
	html += chart_card(__('Contracts by Category'), 'categoryLegend', 'categoryChart');
	html += chart_card(__('Portfolio Value: Consumed vs. Remaining'), 'consumptionLegend', 'consumptionChart');
	html += '</div>';

	html += '</div>'; // /x-data
	html += '</div>'; // /.procurement-dashboard-page
	return html;
}

function stat_icon(path_d) {
	return '<svg width="28" height="28" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="1.5" style="opacity:0.85; flex-shrink:0;">'
		+ '<path stroke-linecap="round" stroke-linejoin="round" d="' + path_d + '" /></svg>';
}

// drilldown, when given, is {doctype, filters} -- the exact set the stat's
// own get_dashboard_summary() query counts (see build_drilldown_attr()).
// The link is a plain data-attribute + delegated click handler (matching
// the existing .rfq-po-link pattern in rfq_comparison.js), not an Alpine
// @click, so the same JSON-in-attribute safety rule applies: esc() before
// embedding, JSON.parse() on click.
function stat_card(bg, x_text_expr, label, path_d, drilldown) {
	var link_attrs = drilldown
		? ' class="dashboard-stat-card-link"' + build_drilldown_attr(drilldown)
		: '';
	return '<div' + link_attrs + ' style="background:' + bg + '; border-radius:12px; padding:1.1rem; display:flex; align-items:center; justify-content:space-between; color:white;">'
		+ '<div>'
		+ '<p style="font-size:26px; font-weight:700; margin:0;" x-text="' + x_text_expr + '"></p>'
		+ '<p style="font-size:11px; margin:4px 0 0; text-transform:uppercase; letter-spacing:0.04em; opacity:0.9;">' + label + '</p>'
		+ '</div>' + stat_icon(path_d) + '</div>';
}

function build_drilldown_attr(drilldown) {
	return ' data-drilldown="' + esc(JSON.stringify(drilldown)) + '"';
}

$(document).on('click', '.dashboard-stat-card-link', function () {
	var payload = JSON.parse(this.dataset.drilldown);
	frappe.set_route('List', payload.doctype, payload.filters);
});

function chart_card(title, legend_id, canvas_id) {
	return '<div class="rich-card" style="padding:1rem;">'
		+ '<div style="font-weight:500; margin-bottom:12px;">' + title + '</div>'
		+ '<div id="' + legend_id + '" style="display:flex; flex-wrap:wrap; gap:10px; margin-bottom:10px;"></div>'
		+ '<div style="height:200px;"><canvas id="' + canvas_id + '"></canvas></div>'
		+ '</div>';
}

// Ported from proc_portal's dashboard.html -- CHART_PALETTE/MUTED_TICK, buildLegend(),
// and the dashboardPage() Alpine component, calling the exact same whitelisted
// proc_portal.api.dashboard.* endpoints. Deliberate adaptations, matching
// rfq_comparison.js's own documented precedent, not business-logic changes:
//   1. frappe.call() instead of raw fetch() -- desk's own call wrapper already
//      handles CSRF/error surfacing natively.
//   2. Chart instances are destroyed via the page-level registry in render()
//      above, before the DOM is replaced, instead of the portal's own
//      per-canvas Chart.getChart(id)+destroy() guards -- those are dropped
//      here entirely, not kept for fidelity, because they're provably dead
//      once the registry-based destroy runs first: by the time this code
//      executes, every canvas is brand new and has never had a chart
//      attached, so Chart.getChart(id) can only ever return nothing.
//   3. No x-init="init()" on the x-data root (see build_page_html() above)
//      -- Alpine already auto-calls a component's own init() method, and
//      the portal's explicit x-init on top of that silently double-fires
//      init() on every load (confirmed via an isolated jsdom+Alpine repro,
//      not assumed). Self-heals in the portal via its own per-canvas
//      destroy guards; would have doubled every API call and chart here.
//   4. buildLegend() now runs item.label through esc() before interpolating
//      it into innerHTML -- the portal's own version doesn't, and item.label
//      is live DB data (supplier/status/category names) that could contain
//      HTML special characters. A small, deliberate hardening applied during
//      the port, not a redesign.
const CHART_PALETTE = ['#2EB2FF', '#5271FF', '#16A34A', '#D97706', '#DC2626'];
const MUTED_TICK = '#898781';

function buildLegend(containerId, items) {
	const el = document.getElementById(containerId);
	if (!el) return;
	el.innerHTML = items.map(item => `
		<div style="display:flex; align-items:center; gap:6px;">
			<span style="width:10px; height:10px; border-radius:2px; background:${item.color}; display:inline-block; flex-shrink:0;"></span>
			<span style="font-size:12px; color:var(--text-secondary);">${esc(item.label)}${item.value !== undefined ? ': ' + esc(item.value) : ''}</span>
		</div>
	`).join('');
}

window.proc_app_dashboardPage = function () {
	return {
		loading: true, summary: {}, portfolio: {},
		get activeContractsCount() {
			const row = (this.portfolio.status_counts || []).find(s => s.status === 'Active');
			return row ? row.count : 0;
		},
		init() {
			Promise.all([
				frappe.call({ method: 'proc_portal.api.dashboard.get_dashboard_summary' }),
				frappe.call({ method: 'proc_portal.api.dashboard.get_requests_by_status' }),
				frappe.call({ method: 'proc_portal.api.dashboard.get_spending_by_month', args: { months: 6 } }),
				frappe.call({ method: 'proc_portal.api.dashboard.get_spending_by_supplier', args: { limit: 5 } }),
				frappe.call({ method: 'proc_portal.api.dashboard.get_rfq_response_status', args: { limit: 5 } }),
				frappe.call({ method: 'proc_portal.api.dashboard.get_procurement_funnel' }),
				frappe.call({ method: 'proc_portal.api.dashboard.get_po_fulfillment_status' }),
				frappe.call({ method: 'proc_portal.api.dashboard.get_contract_expiry_timeline' }),
				frappe.call({ method: 'proc_portal.api.dashboard.get_invoice_aging' }),
				frappe.call({ method: 'proc_portal.api.dashboard.get_contract_portfolio' }),
			]).then(([summary, byStatus, byMonth, bySupplier, rfqStatus, funnel, fulfillment, contractExpiry, invoiceAging, portfolio]) => {
				this.summary = summary.message || {};
				this.portfolio = portfolio.message || {};
				this.loading = false;
				this.$nextTick(() => {
					this.renderCharts(
						byStatus.message || [], byMonth.message || [], bySupplier.message || [], rfqStatus.message || [],
						funnel.message || [], fulfillment.message || {}, contractExpiry.message || [], invoiceAging.message || []
					);
					this.renderPortfolioCharts(this.portfolio);
				});
			});
		},
		renderPortfolioCharts(portfolio) {
			const mutedScale = {
				grid: { display: false },
				ticks: { color: MUTED_TICK },
			};

			const categoryCounts = portfolio.category_counts || [];
			const categoryColors = categoryCounts.map((r, i) => CHART_PALETTE[i % CHART_PALETTE.length]);
			buildLegend('categoryLegend', categoryCounts.map((r, i) => ({ color: categoryColors[i], label: r.category, value: r.count })));
			register_chart(new Chart(document.getElementById('categoryChart'), {
				type: 'doughnut',
				data: {
					labels: categoryCounts.map(r => r.category),
					datasets: [{ data: categoryCounts.map(r => r.count), backgroundColor: categoryColors }],
				},
				options: {
					maintainAspectRatio: false,
					plugins: { legend: { display: false } },
				},
			}));

			const consumed = Number(portfolio.total_consumed || 0);
			const remaining = Math.max(Number(portfolio.total_active_value || 0) - consumed, 0);
			buildLegend('consumptionLegend', [
				{ color: '#2EB2FF', label: 'Consumed', value: '$' + consumed.toLocaleString() },
				{ color: '#E5E7EB', label: 'Remaining', value: '$' + remaining.toLocaleString() },
			]);
			register_chart(new Chart(document.getElementById('consumptionChart'), {
				type: 'bar',
				data: {
					labels: ['Portfolio'],
					datasets: [
						{ label: 'Consumed', data: [consumed], backgroundColor: '#2EB2FF', borderRadius: 3 },
						{ label: 'Remaining', data: [remaining], backgroundColor: '#E5E7EB', borderRadius: 3 },
					],
				},
				options: {
					indexAxis: 'y',
					maintainAspectRatio: false,
					plugins: { legend: { display: false } },
					scales: {
						x: { ...mutedScale, stacked: true },
						y: { ...mutedScale, stacked: true },
					},
				},
			}));
		},
		renderCharts(byStatus, byMonth, bySupplier, rfqStatus, funnel, fulfillment, contractExpiry, invoiceAging) {
			const mutedScale = {
				grid: { display: false },
				ticks: { color: MUTED_TICK },
			};

			const statusColors = byStatus.map((r, i) => CHART_PALETTE[i % CHART_PALETTE.length]);
			buildLegend('statusLegend', byStatus.map((r, i) => ({ color: statusColors[i], label: r.status, value: r.count })));
			register_chart(new Chart(document.getElementById('statusChart'), {
				type: 'bar',
				data: {
					labels: byStatus.map(r => r.status),
					datasets: [{ label: 'Count', data: byStatus.map(r => r.count), backgroundColor: statusColors, borderRadius: 3, barThickness: 16 }],
				},
				options: {
					maintainAspectRatio: false,
					plugins: { legend: { display: false } },
					scales: { x: mutedScale, y: mutedScale },
				},
			}));

			buildLegend('monthLegend', [{ color: '#2EB2FF', label: 'Total PO Spend' }]);
			register_chart(new Chart(document.getElementById('monthChart'), {
				type: 'bar',
				data: {
					labels: byMonth.map(r => r.month),
					datasets: [{ label: 'Total ($)', data: byMonth.map(r => r.total), backgroundColor: '#2EB2FF', borderRadius: 3, barThickness: 30 }],
				},
				options: {
					maintainAspectRatio: false,
					plugins: { legend: { display: false } },
					scales: { x: mutedScale, y: mutedScale },
				},
			}));

			const supplierColors = bySupplier.map((r, i) => CHART_PALETTE[i % CHART_PALETTE.length]);
			const supplierTotalSum = bySupplier.reduce((sum, r) => sum + Number(r.total), 0);
			buildLegend('supplierLegend', bySupplier.map((r, i) => ({
				color: supplierColors[i],
				label: r.supplier,
				value: supplierTotalSum > 0 ? (Number(r.total) / supplierTotalSum * 100).toFixed(1) + '%' : '0%',
			})));
			register_chart(new Chart(document.getElementById('supplierChart'), {
				type: 'doughnut',
				data: {
					labels: bySupplier.map(r => r.supplier),
					datasets: [{ data: bySupplier.map(r => r.total), backgroundColor: supplierColors }],
				},
				options: {
					maintainAspectRatio: false,
					plugins: { legend: { display: false } },
				},
			}));

			buildLegend('rfqLegend', [
				{ color: '#2EB2FF', label: 'Received (bars)' },
				{ color: '#5271FF', label: 'Pending (area)' },
			]);
			register_chart(new Chart(document.getElementById('rfqChart'), {
				data: {
					labels: rfqStatus.map(r => r.rfq),
					datasets: [
						{ type: 'bar', label: 'Received', data: rfqStatus.map(r => r.received), backgroundColor: '#2EB2FF', borderRadius: 4, barThickness: 20 },
						{ type: 'line', label: 'Pending', data: rfqStatus.map(r => r.pending), borderColor: '#5271FF', backgroundColor: 'rgba(82,113,255,0.15)', fill: true, tension: 0.45, pointRadius: 4, borderWidth: 3 },
					],
				},
				options: {
					maintainAspectRatio: false,
					plugins: { legend: { display: false } },
					scales: {
						x: mutedScale,
						y: mutedScale,
					},
				},
			}));

			const funnelColors = funnel.map((r, i) => CHART_PALETTE[i % CHART_PALETTE.length]);
			buildLegend('funnelLegend', funnel.map((r, i) => ({ color: funnelColors[i], label: r.stage, value: r.count })));
			register_chart(new Chart(document.getElementById('funnelChart'), {
				type: 'bar',
				data: {
					labels: funnel.map(r => r.stage),
					datasets: [{ label: 'Count', data: funnel.map(r => r.count), backgroundColor: funnelColors, borderRadius: 3, barThickness: 16 }],
				},
				options: {
					indexAxis: 'y',
					maintainAspectRatio: false,
					plugins: { legend: { display: false } },
					scales: { x: mutedScale, y: mutedScale },
				},
			}));

			const fulfillmentLabels = ['Ordered', 'Received', 'Billed'];
			const fulfillmentData = [fulfillment.ordered_qty || 0, fulfillment.received_qty || 0, fulfillment.billed_qty || 0];
			const fulfillmentColors = [CHART_PALETTE[0], CHART_PALETTE[1], CHART_PALETTE[2]];
			buildLegend('fulfillmentLegend', fulfillmentLabels.map((label, i) => ({ color: fulfillmentColors[i], label, value: fulfillmentData[i] })));
			register_chart(new Chart(document.getElementById('fulfillmentChart'), {
				type: 'bar',
				data: {
					labels: fulfillmentLabels,
					datasets: [{ label: 'Qty', data: fulfillmentData, backgroundColor: fulfillmentColors, borderRadius: 3, barThickness: 30 }],
				},
				options: {
					maintainAspectRatio: false,
					plugins: { legend: { display: false } },
					scales: { x: mutedScale, y: mutedScale },
				},
			}));

			buildLegend('contractExpiryLegend', [{ color: '#E0942E', label: 'Expiring soon' }]);
			register_chart(new Chart(document.getElementById('contractExpiryChart'), {
				type: 'bar',
				data: {
					labels: contractExpiry.map(r => r.bucket),
					datasets: [{ label: 'Contracts', data: contractExpiry.map(r => r.count), backgroundColor: '#E0942E', borderRadius: 3, barThickness: 30 }],
				},
				options: {
					maintainAspectRatio: false,
					plugins: { legend: { display: false } },
					scales: { x: mutedScale, y: mutedScale },
				},
			}));

			const agingColors = invoiceAging.map((r, i) => i === invoiceAging.length - 1 ? '#DC2626' : '#E0942E');
			buildLegend('invoiceAgingLegend', [
				{ color: '#E0942E', label: 'Outstanding' },
				{ color: '#DC2626', label: '90+ days (at risk)' },
			]);
			register_chart(new Chart(document.getElementById('invoiceAgingChart'), {
				type: 'bar',
				data: {
					labels: invoiceAging.map(r => r.bucket),
					datasets: [{ label: 'Invoices', data: invoiceAging.map(r => r.count), backgroundColor: agingColors, borderRadius: 3, barThickness: 30 }],
				},
				options: {
					maintainAspectRatio: false,
					plugins: { legend: { display: false } },
					scales: { x: mutedScale, y: mutedScale },
				},
			}));
		},
	};
};

frappe.query_reports["RFQ Comparison - By Proposal"] = {
	filters: [
		{
			fieldname: "rfq",
			label: __("Request for Quotation"),
			fieldtype: "Link",
			options: "Request for Quotation",
			reqd: 1,
		},
	],
};

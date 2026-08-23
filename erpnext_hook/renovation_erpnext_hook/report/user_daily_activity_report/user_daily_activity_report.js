// Copyright (c) 2026, ERPNext Hook and contributors
// For license information, please see license.txt

frappe.query_reports["User Daily Activity Report"] = {
	"filters": [
		{
			"fieldname": "user",
			"label": __("User"),
			"fieldtype": "Link",
			"options": "User"
		},
		{
			"fieldname": "from_date",
			"label": __("From Date"),
			"fieldtype": "Date",
			"default": frappe.datetime.add_months(frappe.datetime.get_today(), -1),
			"reqd": 1
		},
		{
			"fieldname": "to_date",
			"label": __("To Date"),
			"fieldtype": "Date",
			"default": frappe.datetime.get_today(),
			"reqd": 1
		},
		{
			"fieldname": "view_mode",
			"label": __("View Mode"),
			"fieldtype": "Select",
			"options": [
				{ "value": "Daily Summary", "label": __("Daily Summary") },
				{ "value": "Detailed Timeline", "label": __("Detailed Timeline") }
			],
			"default": "Daily Summary",
			"reqd": 1
		},
		{
			"fieldname": "activity_type",
			"label": __("Activity Type"),
			"fieldtype": "Select",
			"options": "\nLogin / Logout\nCreated Documents\nModified Documents\nComments",
			"depends_on": "eval:doc.view_mode=='Detailed Timeline'"
		}
	]
};

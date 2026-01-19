// Copyright (c) 2019, Leam Technology Systems and contributors
// For license information, please see license.txt

frappe.ui.form.on('Renovation Work Order Modify Request', {
	setup: frm => {
		frm.add_fetch('work_order_no', 'id', 'work_order_id')
		frm.add_fetch('work_order_no', 'property_name', 'property_name')
		frm.add_fetch('work_order_no', 'unit', 'unit')
		frm.add_fetch('work_order_no', 'call_date', 'call_date')
		frm.add_fetch('work_order_no', 'problem_description', 'problem_description')
		frm.add_fetch('work_order_no', 'order_status', 'work_order_status')
	},
	refresh: function(frm) {

	}
});

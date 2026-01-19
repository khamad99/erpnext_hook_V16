frappe.ui.form.on('Expense Entry', {
	validate: (frm) => {
		frm.events.calculate_totals_vat(frm);
	},
	calculate_totals_vat: (frm) => {
		let vat = 0;
		frm.doc.expenses.forEach((doc) => {
			vat += doc.vat_amount;
		});
		frm.set_value("total_vat", vat);
	}
})

frappe.ui.form.on('Expense Entry Item', {
	expenses_remove: (frm) => {
		frm.events.calculate_totals_vat(frm);
	},
	vat_amount: (frm) => {
		frm.events.calculate_totals_vat(frm);
	}
})
// Extend Expense Claim


frappe.ui.form.on("Expense Claim", {
	make_payment_entry: function(frm) {
		return frappe.call({
			method: 'erpnext_hook.utils.expense_claim.get_payment_entry',
			args: {
				"dt": frm.doc.doctype,
				"dn": frm.doc.name
			},
			callback: function(r) {
				var doclist = frappe.model.sync(r.message);
				frappe.set_route("Form", doclist[0].doctype, doclist[0].name);
			}
		});
	}
})


frappe.ui.form.on("Expense Claim Detail", {
	vat_amount: function(frm, cdt, cdn) {
		var child = locals[cdt][cdn];
		var doc = frm.doc;

		if(!child.sanctioned_vat_amount){
			frappe.model.set_value(cdt, cdn, 'sanctioned_vat_amount', child.vat_amount);
		}

		cur_frm.cscript.calculate_vat_total(doc,cdt,cdn);
	},

	sanctioned_vat_amount: function(frm, cdt, cdn) {
		var doc = frm.doc;
		cur_frm.cscript.calculate_vat_total(doc,cdt,cdn);
	},
	expenses_remove: function(frm) {
		var doc = frm.doc;
		cur_frm.cscript.calculate_vat_total(doc,cdt,cdn);
	}

});


cur_frm.cscript.calculate_vat_total = function(doc){
	doc.total_vat_amount = 0;
	doc.total_sanctioned_vat_amount = 0;
	$.each((doc.expenses || []), function(i, d) {
		doc.total_vat_amount += d.vat_amount;
		doc.total_sanctioned_vat_amount += d.sanctioned_vat_amount;
	});

	refresh_field("total_vat_amount");
	refresh_field('total_sanctioned_vat_amount');
};
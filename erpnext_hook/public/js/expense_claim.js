// Extend Expense Claim


frappe.ui.form.on("Expense Claim", {
	refresh: function (frm) {
		frm._project_for_cost_center = frm.doc.project;
		if (frm.doc.workflow_state === 'Reviewed' || frm.doc.status === 'Reviewed' || frm.doc.approval_status === 'Reviewed') {
			setTimeout(() => {
				if (frm.page.menu) {
					frm.page.menu.find('[data-label="Delete"]').closest('li').remove();
				}
			}, 100);
		}
	},
	project: function (frm) {
		// Same rule as the save (set_cost_center_from_project). Drafts only: an
		// edit on a submitted claim would re-post its ledger on Update.
		const old_project = frm._project_for_cost_center;
		frm._project_for_cost_center = frm.doc.project;
		if (frm.doc.docstatus !== 0 || !frm.doc.company) return;

		frappe.call({
			method: 'erpnext_hook.utils.expense_claim.get_header_cost_center',
			args: {
				company: frm.doc.company,
				project: frm.doc.project,
				old_project: old_project,
				cost_center: frm.doc.cost_center
			},
			callback: function (r) {
				if (r.message && r.message !== frm.doc.cost_center) {
					frm.set_value('cost_center', r.message);
				}
			}
		});
	},
	make_payment_entry: function (frm) {
		return frappe.call({
			method: 'erpnext_hook.utils.expense_claim.get_payment_entry',
			args: {
				"dt": frm.doc.doctype,
				"dn": frm.doc.name
			},
			callback: function (r) {
				var doclist = frappe.model.sync(r.message);
				frappe.set_route("Form", doclist[0].doctype, doclist[0].name);
			}
		});
	}
})


frappe.ui.form.on("Expense Claim Detail", {
	vat_amount: function (frm, cdt, cdn) {
		var child = locals[cdt][cdn];
		var doc = frm.doc;

		if (!child.sanctioned_vat_amount) {
			frappe.model.set_value(cdt, cdn, 'sanctioned_vat_amount', child.vat_amount);
		}

		cur_frm.cscript.calculate_vat_total(doc, cdt, cdn);
	},

	sanctioned_vat_amount: function (frm, cdt, cdn) {
		var doc = frm.doc;
		cur_frm.cscript.calculate_vat_total(doc, cdt, cdn);
	},
	expenses_remove: function (frm) {
		var doc = frm.doc;
		cur_frm.cscript.calculate_vat_total(doc, cdt, cdn);
	}

});


cur_frm.cscript.calculate_vat_total = function (doc) {
	doc.total_vat_amount = 0;
	doc.total_sanctioned_vat_amount = 0;
	$.each((doc.expenses || []), function (i, d) {
		doc.total_vat_amount += d.vat_amount;
		doc.total_sanctioned_vat_amount += d.sanctioned_vat_amount;
	});

	refresh_field("total_vat_amount");
	refresh_field('total_sanctioned_vat_amount');
};
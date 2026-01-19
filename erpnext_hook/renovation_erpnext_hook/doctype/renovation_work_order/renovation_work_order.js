// Copyright (c) 2019, Leam Technology Systems and contributors
// For license information, please see license.txt

frappe.ui.form.on('Renovation Work Order', {
	refresh: function(frm) {
		let attachmets = frappe.model.docinfo[frm.doctype][frm.doc.name]['attachments']
		frappe.call({
			method: "erpnext_hook.renovation_erpnext_hook.doctype.renovation_work_order.renovation_work_order.get_womr_attachments",
			args: {
				wo: frm.doc.name
			},
			callback: r => {
				if(r['message']) {
					frappe.model.docinfo[frm.doctype][frm.doc.name]['attachments'] = attachmets.concat(r.message)
					frm.attachments.refresh()
				}
			}
		})
	}
});

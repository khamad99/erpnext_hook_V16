frappe.ui.form.on('Quotation', {
	reset_attachment_from_wo: frm => {
		if (!frm.doc.renovation_work_order) {
			return
		}
		frappe.call({
			method: "erpnext_hook.doc_event.quotation.get_all_attachmetns",
			args: {
				wo: frm.doc.renovation_work_order,
			},
			callback: r => {
				frm.doc.attachments = []
				if (r['message']) {
					r.message.forEach(row=>{
						frm.add_child('attachments', row)
					})
				}
				frm.refresh_field('attachments')
			}
		})
	}
})


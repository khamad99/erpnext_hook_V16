frappe.listview_settings['Renovation Work Order Modify Request'] = {
	add_fields: ["request_status"],
	get_indicator: function(doc) {
		if (doc.request_status==="Approved") {
			return [__("Approved"), "green", "request_status,=,Approved"];
		} else if (doc.docstatus===0 || doc.request_status==="Pending") {
			return [__("Pending"), "orange", "request_status,=,Pending"];
		} else if (doc.request_status==="Rejected") {
			return [__("Rejected"), "red", "request_status,=,Rejected"];
		}
	}
}
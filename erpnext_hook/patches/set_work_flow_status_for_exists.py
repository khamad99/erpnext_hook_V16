import frappe

def execute():
	frappe.reload_doc('renovation_erpnext_hook', 'doctype', 'renovation_work_order_modify_request')
	frappe.db.sql("""update `tabRenovation Work Order Modify Request` set workflow_state = if(strcmp(request_status, "Approved")=0, "Approved", "Canceled")
	where docstatus = 1 and workflow_state="Pending" and request_status !="Pending" """)

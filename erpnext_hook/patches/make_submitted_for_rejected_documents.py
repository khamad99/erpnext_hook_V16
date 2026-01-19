import frappe

def execute():
	frappe.reload_doc('renovation_erpnext_hook', 'doctype', 'renovation_work_order')
	for docname in frappe.get_all('Renovation Work Order Modify Request', [['workflow_state', '=', 'Rejected'], ['docstatus', '=', 0]]):
		doc = frappe.get_doc('Renovation Work Order Modify Request', docname.name)
		doc.submit()

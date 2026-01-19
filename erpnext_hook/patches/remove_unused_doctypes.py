import frappe

def execute():
	for dt in ('Renovation Building', 'Renovation Email Template', 'Renovation Job Order', 'Renovation Job Order Update Request',
	'Renovation Order Status', 'Renovation Property', 'Renovation Sales Order Type', 'Renovation Job Order Modify Request Image', 'Renovation Job Order Category'):
		frappe.delete_doc_if_exists('DocType', dt)
	for field in ('Quotation-job_order_no', 'Quotation-quotation_no', 'Communication-hook_processed'):
		frappe.delete_doc_if_exists('Custom Field', field)

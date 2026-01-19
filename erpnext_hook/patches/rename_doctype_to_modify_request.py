import frappe

def execute():
	frappe.delete_doc_if_exists('DocType', 'Renovation Work Order Update Request', 1)

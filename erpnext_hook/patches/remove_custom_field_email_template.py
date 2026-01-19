import frappe


def execute():
	frappe.delete_doc_if_exists('Custom Field', 'Email Alert-email_template', 1)
	frappe.db.commit()

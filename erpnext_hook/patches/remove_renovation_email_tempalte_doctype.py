import frappe
import os, shutil


def execute():
	frappe.delete_doc_if_exists('DocType', 'Renovation Email Template')
	path = frappe.get_app_path('erpnext_hook', 'renovation_erpnext_hook', 'doctype', 'renovation_email_template')
	if os.path.exists(path):
		shutil.rmtree(path)

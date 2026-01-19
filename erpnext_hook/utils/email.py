from __future__ import unicode_literals
import frappe
import json
from six import string_types


@frappe.whitelist()
def get_email_template(template_name, doc):
	'''Returns the processed HTML of a email template with the given doc'''
	if isinstance(doc, string_types):
		doc = json.loads(doc)

	email_template = frappe.get_doc("Email Template", template_name)
	if email_template.subject.find('doc.') != -1 or email_template.response.find('doc.') != -1:
		doc = {"doc": doc}
	return {
		"subject" : frappe.render_template(email_template.subject, doc),
		"message" : frappe.render_template(email_template.response, doc)
		}

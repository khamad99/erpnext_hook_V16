import frappe
from frappe.utils.pdf import get_pdf
from frappe.utils.file_manager import save_file
import time
from frappe.utils import cstr

def quotation_onload(doc, method):
	load_attachments_from_wo(doc)

def load_attachments_from_wo(quotation, force=False):
	if quotation.renovation_work_order and (force or not len(quotation.get('attachments'))):
		attachments = get_all_attachmetns(quotation.renovation_work_order)
		quotation.set('attachments', attachments)
	
@frappe.whitelist()
def get_all_attachmetns(wo):
	return frappe.db.sql("""select file, title, alternative_text, enabled, vendor, reference_dt, reference_name, details from `tabRenovation Job Order Attachment`
		 where parent='{}' and parentfield="vendor_attachments" and parenttype='Renovation Work Order' and reference_dt in ('Renovation Work Order Modify Request', 'Quotation') and vendor=1""".format(wo), as_dict=True)

def quotation_submit(doc, method):
	generate_pdf_from_quotation(doc)
	add_renovation_modify_task(doc)


def add_renovation_modify_task(quotation):
	if not quotation.renovation_work_order:
		return
	doc = frappe.new_doc('Renovation Modify Task')
	doc.update({
		"work_order": quotation.renovation_work_order,
		"quotation": quotation.name,
		"update_type": "Quotation Submission"
	})

	# Commented out to prevent attaching files from Renovation Work Order. Only the generated quotation should be included.
	# attachments = [{"file": x.file, "title": x.title, "alternative_text": x.alternative_text, "enabled": x.enabled, "vendor": x.vendor, "reference_dt": x.reference_dt, "reference_name": x.reference_name, "details": x.details} for x in quotation.get('attachments')]
	attachments = []
	if quotation.flags.attachment_for_task:
		attachments.append(quotation.flags.attachment_for_task)
	doc.set('attachments', attachments)
	doc.insert(ignore_permissions=True)
	

def generate_pdf_from_quotation(quotation):
	wo = frappe.get_doc('Renovation Work Order', quotation.renovation_work_order)
	html = frappe.get_print(quotation.doctype, quotation.name)
	content = get_pdf(html)
	f = save_file("wo-qit-pdf-{0}.pdf".format(cstr(time.time()).replace('.','_')), content, 'Renovation Work Order', quotation.renovation_work_order, is_private=1)
	wo_vendor_attachement = wo.as_dict().get('vendor_attachments', [])
	quotation.flags.attachment_for_task = {
		'file': f.file_url,
		'title': 'Auto Generated PDF from Quotation {}'.format(quotation.name),
		'reference_dt': quotation.doctype,
		'reference_name': quotation.name,
		'vendor': 1
	}
	wo_vendor_attachement.append(quotation.flags.attachment_for_task)
	wo.set('attachments', wo_vendor_attachement)
	wo.save()

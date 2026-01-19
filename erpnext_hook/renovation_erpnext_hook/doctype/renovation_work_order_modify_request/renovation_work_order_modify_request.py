# -*- coding: utf-8 -*-
# Copyright (c) 2019, Leam Technology Systems and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document
from frappe import _
from frappe.model import default_fields, optional_fields
from frappe.utils.pdf import get_pdf
from frappe.utils.file_manager import save_file
import time
from frappe.utils import cstr
from frappe.desk.form.assign_to import remove, add
import json


class RenovationWorkOrderModifyRequest(Document):
	self_to_wo_field_map = {
		"status": "order_status",
		"signature": "signature",
		"call_date": "call_date",
		"attach_file": "attach_file"
	}

	self_to_wo_field_append = {
		"technician_notes": "technician_notes",
		"internal_technician_notes": "internal_technician_notes"
		}

	def validate(self):
		self.set_missing_vaolues()
		self.ensure_file_records()

	def set_missing_vaolues(self):
		if self.work_order_no:
			wo = frappe.get_doc('Renovation Work Order', self.work_order_no)
			for self_field, wo_field in {'property_name':'property_name', 'unit': 'unit', 'call_date': 'call_date',
				'problem_description': 'problem_description', 'work_order_status':'order_status'}.items():
				if not self.get(self_field):
					self.set(self_field, wo.get(wo_field))

	def ensure_file_records(self):
		"""Ensure File records exist for all attachments in images child table."""
		for row in self.images:
			if not row.file:
				continue
			
			file_url = row.file
			
			# Check if File record exists for this URL attached to this child table row
			existing = frappe.db.exists("File", {
				"file_url": file_url,
				"attached_to_doctype": "Renovation Job Order Attachment",
				"attached_to_name": row.name
			})
			
			if not existing:
				# Check if File record exists with any attachment (might be from upload)
				any_existing = frappe.db.exists("File", {"file_url": file_url})
				
				if not any_existing:
					# Create new File record
					try:
						file_doc = frappe.get_doc({
							"doctype": "File",
							"file_url": file_url,
							"attached_to_doctype": "Renovation Job Order Attachment",
							"attached_to_name": row.name,
							"is_private": 1,
							"folder": "Home/Attachments"
						})
						file_doc.insert(ignore_permissions=True)
					except Exception as e:
						frappe.log_error(f"Failed to create File record for {file_url}: {e}", "File Record Creation")
				else:
					# Update existing File record to link to this attachment
					frappe.db.set_value("File", {"file_url": file_url}, {
						"attached_to_doctype": "Renovation Job Order Attachment",
						"attached_to_name": row.name
					})

	def on_submit(self):
		if self.request_status == "Pending":
			frappe.throw(_("Request Status Must be Approved or Reject. Pending Status can't be submit"))
		elif self.request_status == "Approved":
			self.update_related_doc()
		elif self.request_status == "Rejected":
			self.re_assign_wo_users()
		self.add_renovation_modify_task()

	def update_related_doc(self):
		if self.request_type == "Quotation":
			if self.status=="Canceled":
				quo_doc = frappe.get_doc('Quotation', self.quotation_no)
				quo_doc.declare_order_lost("Order to reject throw Email.")
				quo_doc.save()
			else:
				# ToDo Edit/Make Quotation
				pass
		elif self.work_order_no:
			self.update_wo()

	def update_wo(self):
		wo = frappe.get_doc('Renovation Work Order', self.work_order_no)
		for self_field, wo_field in self.self_to_wo_field_map.items():
			wo.set(wo_field, self.get(self_field))
		for self_field, wo_field in self.self_to_wo_field_append.items():
			if self.get(self_field) and self.get(self_field) != wo.get(wo_field):
				old_val = wo.get(wo_field)
				if old_val:
					old_val += ('\n' + self.get(self_field)) if not (old_val.endswith('\n') or self.get(self_field).startswith('\n')) else self.get(self_field)
				else:
					old_val = self.get(self_field)
				wo.set(wo_field, old_val)
		wo_additinal_attachement_updated = False
		wo_vendor_attachement_updated = False
		wo_additinal_attachement = wo.as_dict().get('addition_attachment', [])
		wo_vendor_attachement = wo.as_dict().get('vendor_attachments', [])
		for row in self.as_dict().get('images', []):
			new_row = {}
			for key, val in row.items():
				if key not in default_fields + optional_fields:
					new_row[key] = val
			if new_row:
				new_row['reference_dt'] = self.doctype
				new_row['reference_name'] = self.name
				if row.enabled:
					wo_additinal_attachement.append(new_row)
					wo_additinal_attachement_updated=True
				elif row.vendor:
					wo_vendor_attachement.append(new_row)
					wo_vendor_attachement_updated=True
		if self.status== "Work Completed":
			html = frappe.get_print(self.doctype, self.name, 'JCR') #self.get_pdf_html()
			content = get_pdf(html)
			f = save_file("woupr-pdf-{0}.pdf".format(cstr(time.time()).replace('.','_')), content, 'Renovation Work Order', self.work_order_no, is_private=1)
			pdf_dict = {
				'file': f.file_url,
				'title': 'Auto Generated PDF from Work Order Modify Request {}'.format(self.name),
				'reference_dt': self.doctype,
				'reference_name': self.name,
				'vendor': 1
			}
			self.flags.generated_pdf = pdf_dict
			wo_vendor_attachement.append(pdf_dict)
			wo_vendor_attachement_updated = True
			wo_additinal_attachement.append({
				'file': f.file_url,
				'reference_dt': self.doctype,
				'reference_name': self.name
			})
			wo_additinal_attachement_updated = True
		if self.attach_file:
			wo_additinal_attachement.append({
				'file': self.attach_file,
				'title': 'Auto Added From WO Status Doc. {}'.format(self.name),
				'reference_dt': self.doctype,
				'reference_name': self.name
			})
			wo_additinal_attachement_updated = True
		
		if wo_vendor_attachement_updated:
			wo.set('vendor_attachments', wo_vendor_attachement)

		if wo_additinal_attachement_updated:
			wo.set('addition_attachment', wo_additinal_attachement)
		
		wo.save()
	
	def add_renovation_modify_task(self):
		doc = frappe.new_doc('Renovation Modify Task')
		if self.status== "Work Completed":
			doc.set('update_type', 'Work Complete')
		else:
			doc.set('update_type', 'Change Status')
		doc.update({
			"work_order": self.work_order_no,
			"rwomr": self.name
		})
		# Commented out as requested to prevent attaching default files
		# doc.insert(ignore_permissions=True) 

		attachments = []
		if self.flags.generated_pdf:
			attachments.append(self.flags.generated_pdf)
		
		doc.set('attachments', attachments)
		doc.flags.ignore_default_attachments = True
		doc.insert(ignore_permissions=True)

	def after_insert(self):
		self.clear_assigned_user_from_wo()

	def clear_assigned_user_from_wo(self):
		if self.work_order_no and self.status in('Request Reassignment', 'Cancel Request', 'Work complete'):
			doctype = 'Renovation Work Order'
			prev_assigned = []
			for assign_to in frappe.db.sql_list("""select owner from `tabToDo`
				where reference_type=%(doctype)s and reference_name=%(name)s""", {"doctype": doctype, "name":self.work_order_no}):
				prev_assigned.append(assign_to)
				remove(doctype, self.work_order_no, assign_to)
			if prev_assigned:
				wo = frappe.get_doc(doctype, self.work_order_no)
				wo.db_set('prev_assigned', json.dumps(prev_assigned))
	
	def re_assign_wo_users(self):
		if self.work_order_no and self.status in('Request Reassignment', 'Cancel Request', 'Work complete'):
			doctype = 'Renovation Work Order'
			doc = frappe.get_doc(doctype, self.work_order_no)
			if doc.prev_assigned:
				for assign_to in json.loads(doc.prev_assigned):
					args = {
						"assign_to": [assign_to],
						"doctype": doctype,
						"name": self.work_order_no 
					}
					add(args)

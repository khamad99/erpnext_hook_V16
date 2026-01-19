# -*- coding: utf-8 -*-
# Copyright (c) 2019, Leam Technology Systems and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document
from frappe.utils import add_days, cint
from frappe.desk.form.load import get_attachments


class RenovationWorkOrder(Document):
	def validate(self):
		self.set_missing_values_for_order()
		# self.sync_additional_attanchments()

	def sync_additional_attanchments(self):
		attachments = get_attachments(self.doctype, self.name)
		exists_files_urls = []
		for tfield in ['attachments', 'vendor_attachments']:
			exists_files_urls += [x.file for x in self.get(tfield, [])]
		addition_attachment = self.as_dict().get('addition_attachment', [])
		existing_files =[x.parent_id for x in addition_attachment]
		has_update = False
		for atta in attachments:
			if atta.name not in existing_files:
				addition_attachment.append({
					"file": atta.file_url,
					"parent_id": atta.name,
					"enabled": 0 if atta.file_url in exists_files_urls else 1
				})
				has_update = True
		if has_update:
			self.set('addition_attachment', addition_attachment)
		# frappe.throw(str(attachments))

	def set_missing_values_for_order(self):
		if self.priority and not self.get('days'):
			days = frappe.get_value('Renovation Priority', self.priority, 'days')
			self.set('days', days)
		if self.posting_date and self.get('days') and not self.due_date:
			self.set('due_date', add_days(self.posting_date, cint(self.days)))


@frappe.whitelist()
def get_womr_attachments(wo):
	womr = [x.name for x in frappe.get_all('Renovation Work Order Modify Request', {'work_order_no': wo, 'request_status': 'Approved', 'docstatus': 1})]
	if not womr:
		return []
	return frappe.get_all("File", fields=["name", "file_name", "file_url", "is_private"],
		filters = {"attached_to_name": ('in', womr), "attached_to_doctype": 'Renovation Work Order Modify Request'})

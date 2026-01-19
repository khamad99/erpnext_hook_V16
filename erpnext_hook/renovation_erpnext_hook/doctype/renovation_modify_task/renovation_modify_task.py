# -*- coding: utf-8 -*-
# Copyright (c) 2019, Leam Technology Systems and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document

class RenovationModifyTask(Document):
	def before_insert(self):
		if self.work_order and not self.flags.ignore_default_attachments and (self.flags.force_fetch_attachments or not self.get('attachments')):
			self.set('attachments', self.get_attachments_for_task_vendor_files())

	def get_attachments_for_task_vendor_files(self):
		return frappe.db.sql("""select file, title, alternative_text, enabled, vendor, reference_dt, reference_name, details from `tabRenovation Job Order Attachment`
		 where parent='{}' and parentfield="vendor_attachments" and parenttype='Renovation Work Order' and reference_dt in ('Renovation Work Order Modify Request', 'Quotation') and vendor=1""".format(self.work_order), as_dict=True)

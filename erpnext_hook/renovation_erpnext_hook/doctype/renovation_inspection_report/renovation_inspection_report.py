# -*- coding: utf-8 -*-
from __future__ import unicode_literals
import frappe
from frappe.model.document import Document
from frappe.utils import flt

class RenovationInspectionReport(Document):
	@frappe.whitelist()
	def make_quotation(self):
		has_items = False
		quotation = frappe.new_doc("Quotation")
		quotation.company = frappe.defaults.get_user_default("Company") or frappe.db.get_single_value("Global Defaults", "default_company")
		quotation.transaction_date = frappe.utils.nowdate()
		
		if self.cost_center:
			quotation.cost_center = self.cost_center
			
		for row in self.get("inspection_checklist", []):
			if flt(row.amount) > 0:
				has_items = True
				description = row.description or ""
				if not description:
					description = f"{row.area or ''} - {row.asset or ''}".strip(" -")
				if row.contractor_comments:
					description += f"\nComments: {row.contractor_comments}"
					
				quotation.append("items", {
					"item_code": "gen",
					"description": description.strip(),
					"qty": 1,
					"rate": flt(row.amount),
					"amount": flt(row.amount)
				})
				
		if not has_items:
			frappe.throw("Cannot create Quotation. No items with amount greater than 0 found in the checklist.")
			
		# Ignore mandatory validations to allow creating the draft Quotation
		# Users will fill the missing mandatory fields (like Customer, Item Code) in the Quotation form.
		quotation.flags.ignore_mandatory = True
		quotation.insert(ignore_permissions=True, ignore_mandatory=True)
		
		# Update status of current doc
		self.db_set('status', 'Quotation Created')
		
		return quotation.name

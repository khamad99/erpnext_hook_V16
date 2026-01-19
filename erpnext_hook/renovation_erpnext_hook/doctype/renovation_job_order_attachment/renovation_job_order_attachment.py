# -*- coding: utf-8 -*-
# Copyright (c) 2019, Leam Technology Systems and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document

class RenovationJobOrderAttachment(Document):
	def has_permission(self, ptype="read", user=None, debug=False, **kwargs):
		if not user:
			user = frappe.session.user
		
		if user == "Guest":
			return False
			
		return True

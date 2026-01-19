# -*- coding: utf-8 -*-
# Copyright (c) 2019, Leam Technology Systems and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document

class RenovationWorkOrderProperty(Document):
	def validate(self):
		self.property_name = self.property_no

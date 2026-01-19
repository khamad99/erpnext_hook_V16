import frappe

def execute():
	for dt, filters in {"Custom Field": {"dt": "Renovation Work Order"}, "Property Setter": {"doc_type": "Renovation Work Order"}}.items():
		for field in frappe.get_all(dt, filters):
			frappe.delete_doc(dt, field.name)

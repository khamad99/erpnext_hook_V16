import frappe


def execute():
	frappe.reload_doc('renovation_erpnext_hook', 'doctype', 'renovation_work_order')
	frappe.reload_doc('renovation_erpnext_hook', 'doctype', 'renovation_work_order_property')
	
	frappe.db.sql("""update `tabRenovation Work Order Property` set name=property_name, property_no=property_name where property_name is not null""")
	frappe.db.sql("""update `tabRenovation Work Order` wo left join `tabRenovation Work Order Property` p on p.name=wo.property_name
		 set wo.property_name=p.property_name, wo.property=p.name, wo.owner_name=p.owner_name where wo.property_name is not null""")

import frappe


def execute():
	frappe.reload_doc('renovation_erpnext_hook', 'doctype', 'renovation_work_order_property')
	frappe.reload_doc('renovation_erpnext_hook', 'doctype', 'renovation_work_order')
	frappe.reload_doc('renovation_erpnext_hook', 'doctype', 'renovation_work_order_modify_request')
	prifix_names = "', '".join(['446', '992', '957', '956', '646', '447', '302', '264', '210', '146', '181', '139', '1085', '1049', '102'])
	frappe.db.sql("""update `tabRenovation Work Order Property` set name = concat('P/', name), property_name = name,  property_no = name where name in ('{}')""".format(prifix_names))
	frappe.db.sql("""update `tabRenovation Work Order` set property = concat('P/', property), property_name = property where property in ('{}')""".format(prifix_names))
	frappe.db.sql("""update `tabRenovation Work Order Modify Request` set property_name = concat('P/', property_name) where property_name in ('{}')""".format(prifix_names))

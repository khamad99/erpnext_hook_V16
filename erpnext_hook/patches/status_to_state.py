import frappe

def execute():
    frappe.reload_doc('renovation_erpnext_hook', 'doctype', 'renovation_modify_task')
    frappe.db.sql("""update `tabRenovation Modify Task` set state=status""")

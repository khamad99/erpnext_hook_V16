import frappe
from frappe.model.rename_doc import get_link_fields

def execute():
    """
        -> Find first order
        -> set first order in all link other order linked
        -> Delelte all other orders
    """
    # Update Link Documents
    linked_with = get_link_fields('Renovation Work Order')
    for lk in linked_with:
        frappe.db.sql("""update `tab{doctype}` dt set {fieldname}=(select min(name) from `tabRenovation Work Order` where id = (select id from `tabRenovation Work Order` where name=dt.{fieldname} limit 1) limit 1)""".format(doctype=lk['parent'], fieldname=lk['fieldname']))
    # Add All children in Min Order
    for dt in ["Renovation Job Order Attachment", "Attachment Status"]:
        frappe.db.sql(""" update `tab{doctype}` dt set parent = (select min(name) from `tabRenovation Work Order` where id=(select id from `tabRenovation Work Order` where name=dt.parent limit 1) limit 1) where parenttype="Renovation Work Order" """.format(doctype=dt))
    frappe.db.commit()
    frappe.db.sql("""update `tabRenovation Work Order` rwo set order_status=COALESCE((select status from `tabRenovation Work Order Modify Request` where work_order_no=rwo.name and request_status="Approved" and docstatus=1 order by max(creation) limit 1), rwo.order_status)""")
    orders = frappe.db.sql_list('''select GROUP_CONCAT(name) from `tabRenovation Work Order` group by id having count(id) > 1''')
    for _ord in orders:
        for _o in _ord.split(',')[1:]:
            try:
                frappe.delete_doc('Renovation Work Order', _o)
            except Exception:
                pass
    frappe.db.commit()
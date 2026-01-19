from __future__ import unicode_literals
import frappe
from frappe.client import get_list


@frappe.whitelist()
def get_all_values(doctype, fields=None, filters=None, order_by=None,
    limit_start=None, limit_page_length=20, parent=None):
    data = get_list(doctype, fields, filters, order_by, limit_start, limit_page_length, parent)
    meta = frappe.get_meta(doctype)
    for d in data:
        get_link_itmes(meta, fields, d)
    return data


@frappe.whitelist()
def get_value(doctype, name):
    if not frappe.db.exists(doctype, name):
        return {}
    doc = frappe.get_doc(doctype, name).as_dict()
    meta = frappe.get_meta(doctype)
    get_link_itmes(meta, '*', doc)
    return doc


def get_link_itmes(meta, fields, data):
    for f in meta.fields:
        if f.get('fieldtype') == "Link" and data.get(f.fieldname) and ( fields in ['*', 'name'] or f.fieldname == fields or f.fieldname in fields):
            data['__{}'.format(f.fieldname)] = frappe.get_doc(f.options, data.get(f.fieldname)).as_dict()

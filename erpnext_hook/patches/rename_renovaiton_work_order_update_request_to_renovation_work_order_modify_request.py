from __future__ import unicode_literals

import frappe
from frappe import _
from frappe.core.doctype.deleted_document.deleted_document import restore
from frappe.model.rename_doc import validate_rename, get_link_fields, update_link_field_values, \
	rename_dynamic_links, update_user_settings, rename_doctype, rename_password, cint, update_attachments, rename_versions, \
		update_autoname_field, update_child_docs
from pymysql.err import InternalError


def rename_doc(doctype, old, new, force=False, merge=False, ignore_permissions=False, ignore_if_exists=False):
	"""
		Renames a doc(dt, old) to doc(dt, new) and
		updates all linked fields of type "Link"
	"""
	if not frappe.db.exists(doctype, old):
		return

	if ignore_if_exists and frappe.db.exists(doctype, new):
		return

	if old==new:
		frappe.msgprint(_('Please select a new name to rename'))
		return

	force = cint(force)
	merge = cint(merge)

	meta = frappe.get_meta(doctype)

	# call before_rename
	old_doc = frappe.get_doc(doctype, old)
	out = old_doc.run_method("before_rename", old, new, merge) or {}
	new = (out.get("new") or new) if isinstance(out, dict) else (out or new)

	if doctype != "DocType":
		new = validate_rename(doctype, new, meta, merge, force, ignore_permissions)

	if not merge:
		rename_parent_and_child(doctype, old, new, meta)

	# update link fields' values
	frappe.flags.link_fields = {}
	link_fields = get_link_fields(doctype)
	update_link_field_values(link_fields, old, new, doctype)

	rename_dynamic_links(doctype, old, new)

	# save the user settings in the db
	update_user_settings(old, new, link_fields)

	if doctype=='DocType':
		rename_doctype(doctype, old, new, force)

	update_attachments(doctype, old, new)

	rename_versions(doctype, old, new)

	# call after_rename
	new_doc = frappe.get_doc(doctype, new)

	# copy any flags if required
	new_doc._local = getattr(old_doc, "_local", None)

	try:
		new_doc.run_method("after_rename", old, new, merge)
	except InternalError:
		old_table_columns = frappe.db.get_table_columns(old)
		new_table_columns = frappe.db.get_table_columns(new)
		columns = [f for f in old_table_columns if f in new_table_columns]
		frappe.db.sql("INSERT INTO `tab{new}` ({col}) SELECT {col} FROM `tab{old}`".format(col=', '.join(columns), new=new, old=old))
		frappe.db.sql_ddl("DROP TABLE `tab%s`"%old)
	except Exception:
		pass

	if not merge:
		rename_password(doctype, old, new)

	# update user_permissions
	frappe.db.sql("""update tabDefaultValue set defvalue=%s where parenttype='User Permission'
		and defkey=%s and defvalue=%s""", (new, doctype, old))

	if merge:
		new_doc.add_comment('Edit', _("merged {0} into {1}").format(frappe.bold(old), frappe.bold(new)))
	else:
		new_doc.add_comment('Edit', _("renamed from {0} to {1}").format(frappe.bold(old), frappe.bold(new)))

	if merge:
		frappe.delete_doc(doctype, old)

	frappe.clear_cache()
	frappe.enqueue('frappe.utils.global_search.rebuild_for_doctype', doctype=doctype)

	return new


def rename_parent_and_child(doctype, old, new, meta):
	# rename the doc
	try:
		frappe.db.sql("update `tab%s` set name=%s where name=%s" % (frappe.db.escape(doctype), '%s', '%s'),
		(new, old))
	except Exception as e:
		print(e)
	update_autoname_field(doctype, new, meta)
	update_child_docs(old, new, meta)


def execute():
	if not frappe.db.exists('DocType', 'Renovation Work Order Update Request') and frappe.db.exists('Deleted document', {'deleted_name': 'Renovation Work Order Update Request', 'deleted_doctype': 'DocType', 'restored': 0}):
		deleted_document = frappe.db.get_value('Deleted document', {'deleted_name': 'Renovation Work Order Update Request', 'deleted_doctype': 'DocType', 'restored': 0})
		restore(deleted_document)
	
	if frappe.db.table_exists("Renovation Work Order Update Request"):
		rename_doc('DocType', 'Renovation Work Order Update Request', 'Renovation Work Order Modify Request', force=True)
		frappe.reload_doc('renovation_erpnext_hook', 'doctype', 'renovation_work_order_modify_request')

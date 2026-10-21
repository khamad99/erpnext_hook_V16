import frappe

CUSTOM_FIELD = "Notification-email_template"


def remove_custom_email_template_field():
	"""Delete the old custom Notification.email_template once frappe ships the field.

	Newer frappe v16 releases (checked on 16.52) have a standard `email_template` field on
	Notification. A custom field with the same name then makes the field appear twice in the
	meta and blocks Customize Form.

	Runs after every migrate, because a one-time patch would run and be logged on an older
	frappe, before the standard field exists. On older frappe it does nothing. The column and
	its values stay: the standard field uses the same column.
	"""
	if not frappe.db.exists("Custom Field", CUSTOM_FIELD):
		return
	if not frappe.db.exists("DocField", {"parent": "Notification", "fieldname": "email_template"}):
		return
	frappe.delete_doc("Custom Field", CUSTOM_FIELD, ignore_permissions=True)
	print("Removed Custom Field Notification-email_template: frappe now has this field.")

# -*- coding: utf-8 -*-
# Permission utilities for erpnext_hook

import frappe

# DocTypes for which non-Guest users should always have file access
ALLOWED_FILE_DOCTYPES = [
    "Renovation Job Order Attachment",
    "Renovation Work Order Modify Request",
    "Renovation Work Order",
]

def file_has_permission(doc, ptype=None, user=None, debug=False):
    """
    Custom has_permission for File DocType in erpnext_hook.
    Allows all logged-in users to access files attached to Renovation DocTypes.
    For out-of-scope files, standalone files, or unsaved parent documents,
    delegates directly to Frappe's standard File has_permission logic.
    """
    from frappe.core.doctype.file.file import has_permission as frappe_file_has_permission

    try:
        user = user or frappe.session.user

        if not doc:
            return frappe_file_has_permission(doc, ptype=ptype, user=user, debug=debug)

        attached_to_doctype = getattr(doc, "attached_to_doctype", None)

        # 1. Enforce app-specific rules for Renovation DocTypes
        if attached_to_doctype in ALLOWED_FILE_DOCTYPES:
            if user == "Guest":
                return False
            return True

        # 2. For all other files (standalone, unsaved parent, or non-Renovation DocTypes),
        # delegate to standard Frappe file permission check
        return frappe_file_has_permission(doc, ptype=ptype, user=user, debug=debug)

    except Exception as e:
        frappe.log_error(f"Error in file_has_permission hook: {e}", "File Perm Hook")
        return frappe_file_has_permission(doc, ptype=ptype, user=user, debug=debug)


def renovation_attachment_has_permission(doc, ptype=None, user=None, debug=False):
    """
    Custom has_permission for Renovation Job Order Attachment (Child Table).
    child tables (like this) usually inherit from parent, but this hook ensures specific logic if needed.
    """
    user = user or frappe.session.user
    
    # Allow all users except Guest
    if user != "Guest":
        return True
    return False


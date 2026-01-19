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
    Custom has_permission for File DocType.
    Allows all logged-in users to access files attached to Renovation DocTypes.
    """
    user = user or frappe.session.user
    
    # Debug logging
    # frappe.log_error(f"file_has_permission called: attached_to={doc.attached_to_doctype}, user={user}", "File Perm Hook")
    
    # Check if file is attached to allowed Renovation DocTypes
    if doc.attached_to_doctype in ALLOWED_FILE_DOCTYPES:
        # Allow all users except Guest
        if user != "Guest":
            # frappe.log_error(f"Allowing access for {user} to {doc.attached_to_doctype}", "File Perm Hook")
            return True
        # frappe.log_error(f"Denying Guest", "File Perm Hook")
        return False
    
    # For other doctypes, return None to let standard permission system handle it
    # Returning True allows access, False denies, None passes to next check (standard)
    return True


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


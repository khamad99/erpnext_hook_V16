# -*- coding: utf-8 -*-
from __future__ import unicode_literals

__version__ = '0.0.1'

# Monkey-patch File.has_permission to allow all users access to private files
import frappe
from frappe.core.doctype.file import file as file_module

# Store original function
_original_file_has_permission = file_module.has_permission

def _patched_file_has_permission(doc, ptype=None, user=None, debug=False):
    """Patched has_permission for File DocType.
    Allows all logged-in users to access private files.
    """
    user = user or frappe.session.user
    
    # Allow explicit access for Renovation Job Order Attachment (even for Guests)
    if doc.attached_to_doctype == "Renovation Job Order Attachment":
        return True

    # Allow all users except Guest to access private files
    if user != "Guest":
        return True
    

    # Deny Guest access to private files
    if doc.is_private:
        return False
    
    # Fall back to original logic for public files
    return _original_file_has_permission(doc, ptype, user, debug)

# Apply patch to File.has_permission
file_module.has_permission = _patched_file_has_permission

# ----------------------------------------------------------------------------
# Patch find_file_by_url to ignore permissions during search
# This is needed because get_all will filter out private files for Guests
# before is_downloadable() (and our has_permission patch) can even run.
# ----------------------------------------------------------------------------
from frappe.core.doctype.file import utils as file_utils
import frappe.handler as handler_module

def _patched_find_file_by_url(path, name=None):
    filters = {"file_url": str(path)}
    if name:
        filters["name"] = str(name)

    # FIXED: Added ignore_permissions=True
    files = frappe.get_all("File", filters=filters, fields="*", ignore_permissions=True)

    for file_data in files:
        file_doc = frappe.get_doc(doctype="File", **file_data)
        if file_doc.is_downloadable():
            return file_doc
    return None

# Apply patch to original module AND handler which imports it
file_utils.find_file_by_url = _patched_find_file_by_url
handler_module.find_file_by_url = _patched_find_file_by_url

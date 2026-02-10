# -*- coding: utf-8 -*-
from __future__ import unicode_literals

app_name = "erpnext_hook"
app_title = "Erpnext Hook"
app_publisher = "Leam Technology Systems"
app_description = "ERPNext Hook App"
app_icon = "octicon octicon-file-directory"
app_color = "grey"
app_email = "help@leam.ae"
app_license = "MIT"

# Includes in <head>
# ------------------
fixtures = [
    {
        "dt": "Custom Field",
        "filters": [["app_name", "=", "erpnext_hook"]]
    },
    {
        "dt": "Property Setter",
        "filters": [["app_name", "=", "erpnext_hook"]]
    },
    {
        "dt": "Custom DocPerm",
        "filters": [["parent", "=", "Workflow"]]
    }, "Renovation Proposal", "Renovation Work Order Type", "Renovation Work Order Status",
    {
        "dt": "Workflow",
        "filters": [["name", "in", ["RWOMR Two Level Approval"]]]
    },
    {
        "dt": "Workflow State",
        "filters": [["name", "in", ["Approved by first level", "Canceled"]]]
    },
    {
        "dt": "Client Script",
        "filters": [["name", "in", ["Contract", "Project"]]]
    },
    {
        "dt": "Notification",
        "filters": [["name", "in", ["Retention Release", "Cheque Payment Reminder (10 days)",
                                    "Cheque Payment Reminder (5 days)",
                                    "Cheque Payment Reminder (1 day)"]]]
    },
    {
        "dt": "Email Template",
        "filters": [["name", "in", ["Cheque Payment Reminder", "Retention Release"]]]
    }
]

# include js, css files in header of desk.html
# app_include_css = "/assets/erpnext_hook/css/erpnext_hook.css"
# app_include_js = "assets/js/erpnext_hook.min.js"

# include js, css files in header of web template
# web_include_css = "/assets/erpnext_hook/css/erpnext_hook.css"
# web_include_js = "/assets/erpnext_hook/js/erpnext_hook.js"

# include js in page
# page_js = {"page" : "public/js/file.js"}

# include js in doctype views
doctype_js = {
    "Notification": "public/js/notification.js",
    "Expense Claim": "public/js/expense_claim.js",
    "Quotation": "public/js/quotation.js"
}
# doctype_list_js = {"doctype" : "public/js/doctype_list.js"}
# doctype_tree_js = {"doctype" : "public/js/doctype_tree.js"}
# doctype_calendar_js = {"doctype" : "public/js/doctype_calendar.js"}

# Home Pages
# ----------

# application home page (will override Website Settings)
# home_page = "login"

# website user home page (by Role)
# role_home_page = {
#	"Role": "home_page"
# }

# Website user home page (by function)
# get_website_user_home_page = "erpnext_hook.utils.get_home_page"

# Generators
# ----------

# automatically create page for each record of this doctype
# website_generators = ["Web Page"]

# Installation
# ------------

# before_install = "erpnext_hook.install.before_install"
# after_install = "erpnext_hook.install.after_install"

# Desk Notifications
# ------------------
# See frappe.core.notifications.get_notification_config

# notification_config = "erpnext_hook.notifications.get_notification_config"

# Permissions
# -----------
# Permissions evaluated in scripted ways

# permission_query_conditions = {
# 	"Event": "frappe.desk.doctype.event.event.get_permission_query_conditions",
# }
#
has_permission = {
	"File": "erpnext_hook.utils.permissions.file_has_permission",
	"Renovation Job Order Attachment": "erpnext_hook.utils.permissions.renovation_attachment_has_permission",
}

# Document Events
# ---------------
# Hook on document methods and events

doc_events = {
    "Expense Claim": {
        "on_submit": "erpnext_hook.utils.expense_claim.on_event_for_expense_claim",
        "on_cancel": "erpnext_hook.utils.expense_claim.on_event_for_expense_claim"
    },
    "Quotation": {
        "onload": "erpnext_hook.doc_event.quotation.quotation_onload",
        "on_submit": "erpnext_hook.doc_event.quotation.quotation_submit"
    }
}

# Scheduled Tasks
# ---------------

# scheduler_events = {
# 	"all": [
# 		"erpnext_hook.tasks.all"
# 	],
# 	"daily": [
# 		"erpnext_hook.tasks.daily"
# 	],
# 	"hourly": [
# 		"erpnext_hook.tasks.hourly"
# 	],
# 	"weekly": [
# 		"erpnext_hook.tasks.weekly"
# 	]
# 	"monthly": [
# 		"erpnext_hook.tasks.monthly"
# 	]
# }

# Testing
# -------

# before_tests = "erpnext_hook.install.before_tests"

# Overriding Whitelisted Methods
# ------------------------------
#
override_whitelisted_methods = {
    "frappe.email.doctype.email_template.email_template.get_email_template": "erpnext_hook.utils.email.get_email_template"
}

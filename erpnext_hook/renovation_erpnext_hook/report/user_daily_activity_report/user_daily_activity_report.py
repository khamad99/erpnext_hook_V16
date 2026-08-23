# Copyright (c) 2026, ERPNext Hook and contributors
# For license information, please see license.txt

import frappe
from collections import defaultdict

def execute(filters=None):
    if not filters:
        filters = {}

    view_mode = filters.get("view_mode") or "Daily Summary"

    if view_mode == "Detailed Timeline":
        columns = get_timeline_columns()
        data = get_detailed_timeline(filters)
    else:
        columns = get_summary_columns()
        data = get_daily_summary(filters)

    return columns, data

def get_summary_columns():
    return [
        {
            "label": "Date",
            "fieldname": "activity_date",
            "fieldtype": "Date",
            "width": 110
        },
        {
            "label": "User",
            "fieldname": "user",
            "fieldtype": "Link",
            "options": "User",
            "width": 200
        },
        {
            "label": "Full Name",
            "fieldname": "full_name",
            "fieldtype": "Data",
            "width": 160
        },
        {
            "label": "First Login",
            "fieldname": "first_login",
            "fieldtype": "Time",
            "width": 100
        },
        {
            "label": "Last Logout",
            "fieldname": "last_logout",
            "fieldtype": "Time",
            "width": 100
        },
        {
            "label": "Total Logins",
            "fieldname": "total_logins",
            "fieldtype": "Int",
            "width": 100
        },
        {
            "label": "Session Timeouts",
            "fieldname": "timeouts",
            "fieldtype": "Int",
            "width": 120
        },
        {
            "label": "Work Orders Created",
            "fieldname": "work_orders_created",
            "fieldtype": "Int",
            "width": 150
        },
        {
            "label": "Comments Added",
            "fieldname": "comments_added",
            "fieldtype": "Int",
            "width": 130
        },
        {
            "label": "Documents Modified",
            "fieldname": "docs_modified",
            "fieldtype": "Int",
            "width": 140
        },
        {
            "label": "IP Address(es)",
            "fieldname": "ip_addresses",
            "fieldtype": "Data",
            "width": 180
        }
    ]

def get_timeline_columns():
    return [
        {
            "label": "Timestamp",
            "fieldname": "timestamp",
            "fieldtype": "Datetime",
            "width": 160
        },
        {
            "label": "User",
            "fieldname": "user",
            "fieldtype": "Link",
            "options": "User",
            "width": 190
        },
        {
            "label": "Full Name",
            "fieldname": "full_name",
            "fieldtype": "Data",
            "width": 150
        },
        {
            "label": "Activity Type",
            "fieldname": "activity_type",
            "fieldtype": "Data",
            "width": 140
        },
        {
            "label": "Reference DocType",
            "fieldname": "reference_doctype",
            "fieldtype": "Link",
            "options": "DocType",
            "width": 170
        },
        {
            "label": "Reference Name",
            "fieldname": "reference_name",
            "fieldtype": "Dynamic Link",
            "options": "reference_doctype",
            "width": 180
        },
        {
            "label": "Details / Subject",
            "fieldname": "description",
            "fieldtype": "Data",
            "width": 300
        },
        {
            "label": "IP Address",
            "fieldname": "ip_address",
            "fieldtype": "Data",
            "width": 140
        }
    ]

def get_daily_summary(filters):
    user_filter = filters.get("user")
    from_date = filters.get("from_date")
    to_date = filters.get("to_date")

    conditions = ["creation >= %(from_date)s", "creation <= %(to_date_end)s"]
    params = {
        "from_date": from_date,
        "to_date_end": f"{to_date} 23:59:59"
    }

    user_cond = ""
    if user_filter:
        user_cond = "AND user = %(user)s"
        params["user"] = user_filter

    user_owner_cond = ""
    if user_filter:
        user_owner_cond = "AND owner = %(user)s"

    summary_map = defaultdict(lambda: {
        "activity_date": None,
        "user": None,
        "full_name": None,
        "first_login": None,
        "last_logout": None,
        "total_logins": 0,
        "timeouts": 0,
        "work_orders_created": 0,
        "comments_added": 0,
        "docs_modified": 0,
        "ip_set": set()
    })

    # 1. Activity Logs (Logins / Logouts)
    act_query = f"""
        SELECT 
            user,
            full_name,
            DATE(creation) as act_date,
            operation,
            subject,
            TIME(creation) as act_time,
            ip_address
        FROM `tabActivity Log`
        WHERE {' AND '.join(conditions)} {user_cond}
        ORDER BY creation ASC
    """
    act_logs = frappe.db.sql(act_query, params, as_dict=True)

    for log in act_logs:
        key = (log.user, str(log.act_date))
        item = summary_map[key]
        item["activity_date"] = log.act_date
        item["user"] = log.user
        item["full_name"] = log.full_name or log.user

        if log.operation == "Login":
            item["total_logins"] += 1
            if not item["first_login"] or log.act_time < item["first_login"]:
                item["first_login"] = log.act_time
        elif log.operation == "Logout":
            if not item["last_logout"] or log.act_time > item["last_logout"]:
                item["last_logout"] = log.act_time
            if log.subject and "Session Expired" in log.subject:
                item["timeouts"] += 1

        if log.ip_address:
            item["ip_set"].add(log.ip_address)

    # 2. Renovation Work Orders Created
    wo_query = f"""
        SELECT 
            owner as user,
            DATE(creation) as act_date,
            COUNT(*) as wo_count
        FROM `tabRenovation Work Order`
        WHERE {' AND '.join(conditions)} {user_owner_cond}
        GROUP BY owner, DATE(creation)
    """
    wo_logs = frappe.db.sql(wo_query, params, as_dict=True)

    for wo in wo_logs:
        key = (wo.user, str(wo.act_date))
        item = summary_map[key]
        item["activity_date"] = wo.act_date
        item["user"] = wo.user
        item["work_orders_created"] = wo.wo_count

    # 3. Comments Added
    comm_query = f"""
        SELECT 
            owner as user,
            DATE(creation) as act_date,
            COUNT(*) as comm_count
        FROM `tabComment`
        WHERE {' AND '.join(conditions)} {user_owner_cond}
        GROUP BY owner, DATE(creation)
    """
    comm_logs = frappe.db.sql(comm_query, params, as_dict=True)

    for comm in comm_logs:
        key = (comm.user, str(comm.act_date))
        item = summary_map[key]
        item["activity_date"] = comm.act_date
        item["user"] = comm.user
        item["comments_added"] = comm.comm_count

    # 4. Version Modifications
    ver_query = f"""
        SELECT 
            owner as user,
            DATE(creation) as act_date,
            COUNT(*) as ver_count
        FROM `tabVersion`
        WHERE {' AND '.join(conditions)} {user_owner_cond}
        GROUP BY owner, DATE(creation)
    """
    ver_logs = frappe.db.sql(ver_query, params, as_dict=True)

    for ver in ver_logs:
        key = (ver.user, str(ver.act_date))
        item = summary_map[key]
        item["activity_date"] = ver.act_date
        item["user"] = ver.user
        item["docs_modified"] = ver.ver_count

    # Build final rows
    user_fullname_map = {}
    users_list = frappe.get_all("User", fields=["name", "full_name"])
    for u in users_list:
        user_fullname_map[u.name] = u.full_name

    data = []
    for (user, date_str), row in summary_map.items():
        if not row["full_name"]:
            row["full_name"] = user_fullname_map.get(user, user)
        row["ip_addresses"] = ", ".join(sorted(row["ip_set"]))
        data.append(row)

    data.sort(key=lambda x: (str(x["activity_date"]) if x["activity_date"] else "", x["user"] or ""), reverse=True)
    return data

def get_detailed_timeline(filters):
    user_filter = filters.get("user")
    from_date = filters.get("from_date")
    to_date = filters.get("to_date")
    act_type_filter = filters.get("activity_type")

    conditions = ["creation >= %(from_date)s", "creation <= %(to_date_end)s"]
    params = {
        "from_date": from_date,
        "to_date_end": f"{to_date} 23:59:59"
    }

    user_cond = ""
    if user_filter:
        user_cond = "AND user = %(user)s"
        params["user"] = user_filter

    user_owner_cond = ""
    if user_filter:
        user_owner_cond = "AND owner = %(user)s"

    user_fullname_map = {}
    users_list = frappe.get_all("User", fields=["name", "full_name"])
    for u in users_list:
        user_fullname_map[u.name] = u.full_name

    timeline = []

    # 1. Logins and Logouts
    if not act_type_filter or act_type_filter == "Login / Logout":
        act_query = f"""
            SELECT 
                creation as timestamp,
                user,
                full_name,
                operation as activity_type,
                'Activity Log' as reference_doctype,
                name as reference_name,
                subject as description,
                ip_address
            FROM `tabActivity Log`
            WHERE {' AND '.join(conditions)} {user_cond}
            ORDER BY creation DESC
            LIMIT 1000
        """
        act_rows = frappe.db.sql(act_query, params, as_dict=True)
        timeline.extend(act_rows)

    # 2. Created Renovation Work Orders
    if not act_type_filter or act_type_filter == "Created Documents":
        wo_query = f"""
            SELECT 
                creation as timestamp,
                owner as user,
                order_type,
                'Created Document' as activity_type,
                'Renovation Work Order' as reference_doctype,
                name as reference_name,
                CONCAT('Created ', order_type, ': ', name) as description,
                NULL as ip_address
            FROM `tabRenovation Work Order`
            WHERE {' AND '.join(conditions)} {user_owner_cond}
            ORDER BY creation DESC
            LIMIT 1000
        """
        wo_rows = frappe.db.sql(wo_query, params, as_dict=True)
        for r in wo_rows:
            r["full_name"] = user_fullname_map.get(r.user, r.user)
        timeline.extend(wo_rows)

    # 3. Comments Added
    if not act_type_filter or act_type_filter == "Comments":
        comm_query = f"""
            SELECT 
                creation as timestamp,
                owner as user,
                'Comment Added' as activity_type,
                reference_doctype,
                reference_name,
                content as description,
                NULL as ip_address
            FROM `tabComment`
            WHERE {' AND '.join(conditions)} {user_owner_cond}
            ORDER BY creation DESC
            LIMIT 1000
        """
        comm_rows = frappe.db.sql(comm_query, params, as_dict=True)
        for r in comm_rows:
            r["full_name"] = user_fullname_map.get(r.user, r.user)
        timeline.extend(comm_rows)

    # 4. Modifications (Version logs)
    if not act_type_filter or act_type_filter == "Modified Documents":
        ver_query = f"""
            SELECT 
                creation as timestamp,
                owner as user,
                'Modified Document' as activity_type,
                ref_doctype as reference_doctype,
                docname as reference_name,
                'Modified document fields' as description,
                NULL as ip_address
            FROM `tabVersion`
            WHERE {' AND '.join(conditions)} {user_owner_cond}
            ORDER BY creation DESC
            LIMIT 1000
        """
        ver_rows = frappe.db.sql(ver_query, params, as_dict=True)
        for r in ver_rows:
            r["full_name"] = user_fullname_map.get(r.user, r.user)
        timeline.extend(ver_rows)

    timeline.sort(key=lambda x: str(x["timestamp"]), reverse=True)
    return timeline[:2000]

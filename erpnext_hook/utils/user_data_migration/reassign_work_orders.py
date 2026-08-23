"""
Reassign Renovation Work Order Ownership, Comments, Version Logs, and Activity Logs.

Usage:
    bench --site erp.almaidana.ae execute erpnext_hook.utils.user_data_migration.reassign_work_orders.run

Configuration:
    Edit the `USERS` list below to define which users to assign records to,
    their active date windows, and re-run the script.
"""

import frappe
import random
import string
from datetime import timedelta
from itertools import cycle
from collections import defaultdict


# ─────────────────────────────────────────────
# CONFIGURATION — Edit this section as needed
# ─────────────────────────────────────────────

USERS = [
    {
        "email": "amani.bakheet@almaidana.ae",
        "full_name": "Amani Bakheet",
        "start": "2023-07-12",   # Date from which records are assigned to this user
        "end":   "2026-07-02",   # Last date (inclusive) for this user's window
    },
    {
        "email": "hasna.ghanem@almaidana.ae",
        "full_name": "Hasna Ghanem",
        "start": "2024-12-19",
        "end":   "2026-07-18",
    },
    {
        "email": "ameera.saad@almaidana.ae",
        "full_name": "Ameera Saad",
        "start": "2025-12-16",
        "end":   "2026-07-30",
    },
]

# Source owner — records currently owned by this user will be reassigned
SOURCE_OWNER = "vendor-cafe@hook.ae"

# Overall date window — only records within this range are affected
OVERALL_FROM = "2023-07-12"
OVERALL_TO   = "2026-07-30 23:59:59"

# Period-based Activity Log reassignment (Login/Logout)
# These define which existing login/logout records are reassigned to each user.
# The periods must be mutually exclusive and together cover OVERALL_FROM to OVERALL_TO.
ACTIVITY_LOG_PERIODS = [
    {
        "user":      "amani.bakheet@almaidana.ae",
        "full_name": "Amani Bakheet",
        "from":      "2023-07-12",
        "to":        "2024-12-18",  # exclusive upper bound handled via < '2024-12-19'
    },
    {
        "user":      "hasna.ghanem@almaidana.ae",
        "full_name": "Hasna Ghanem",
        "from":      "2024-12-19",
        "to":        "2025-12-15",  # exclusive upper bound handled via < '2025-12-16'
    },
    {
        "user":      "ameera.saad@almaidana.ae",
        "full_name": "Ameera Saad",
        "from":      "2025-12-16",
        "to":        "2026-07-30",
    },
]

# ─────────────────────────────────────────────


def chunk_list(lst, n=500):
    for i in range(0, len(lst), n):
        yield lst[i:i + n]


def random_id(length=10):
    return ''.join(random.choices(string.ascii_lowercase + string.digits, k=length))


def run():
    print("=" * 60)
    print("Starting Renovation Work Order Reassignment")
    print("=" * 60)

    user_map = {u["email"]: u for u in USERS}

    # ── Step 1: Fetch all affected work orders ──────────────────
    records = frappe.db.sql("""
        SELECT name, creation, DATE(creation) as wo_date
        FROM `tabRenovation Work Order`
        WHERE owner = %(source_owner)s
          AND creation >= %(from_date)s
          AND creation <= %(to_date)s
        ORDER BY creation
    """, {"source_owner": SOURCE_OWNER, "from_date": OVERALL_FROM, "to_date": OVERALL_TO}, as_dict=True)

    print(f"\nFound {len(records)} Renovation Work Orders to reassign.")

    # ── Step 2: Round-robin distribute by date ──────────────────
    user_wo_map = defaultdict(list)
    user_daily_records = defaultdict(lambda: defaultdict(list))
    current_date = None
    rr_iter = None

    for rec in records:
        d = str(rec.wo_date)
        if d != current_date:
            current_date = d
            active = [u for u in USERS if u["start"] <= d <= u["end"]]
            if not active:
                print(f"  ⚠ No active user for date {d} — skipping.")
                continue
            rr_iter = cycle(active)

        assigned_user = next(rr_iter)
        user_email = assigned_user["email"]
        user_wo_map[user_email].append(rec.name)
        user_daily_records[user_email][d].append(rec.creation)

    for u in USERS:
        print(f"  → {u['email']}: {len(user_wo_map[u['email']])} records")

    # ── Step 3: Batch update Work Orders, Comments, Versions ────
    print("\nUpdating tabRenovation Work Order, tabComment, tabVersion...")
    for user_email, wo_names in user_wo_map.items():
        if not wo_names:
            continue
        print(f"  Updating {len(wo_names)} records for {user_email}...")
        for chunk in chunk_list(wo_names, 500):
            frappe.db.sql("""
                UPDATE `tabRenovation Work Order`
                SET owner = %s, modified_by = %s
                WHERE name IN %s
            """, (user_email, user_email, tuple(chunk)))

            frappe.db.sql("""
                UPDATE `tabComment`
                SET owner = %s, modified_by = %s
                WHERE reference_doctype = 'Renovation Work Order'
                  AND reference_name IN %s
                  AND owner = %s
            """, (user_email, user_email, tuple(chunk), SOURCE_OWNER))

            frappe.db.sql("""
                UPDATE `tabVersion`
                SET owner = %s, modified_by = %s
                WHERE ref_doctype = 'Renovation Work Order'
                  AND docname IN %s
                  AND owner = %s
            """, (user_email, user_email, tuple(chunk), SOURCE_OWNER))

    # ── Step 4: Create new Login/Logout records ─────────────────
    print("\nCreating simulated Login/Logout Activity Log records...")
    login_count = 0

    for user_email, daily in user_daily_records.items():
        user_info = user_map[user_email]
        for date_str, timestamps in daily.items():
            if not timestamps:
                continue
            earliest = min(timestamps)
            login_offset = random.randint(5, 20)
            login_time = earliest - timedelta(minutes=login_offset, seconds=random.randint(0, 59))

            frappe.db.sql("""
                INSERT INTO `tabActivity Log`
                (name, creation, modified, modified_by, owner, docstatus,
                 user, operation, status, full_name)
                VALUES (%s, %s, %s, %s, %s, 0, %s, 'Login', 'Success', %s)
            """, (random_id(10), login_time, login_time, user_email, user_email,
                  user_email, user_info["full_name"]))

            logout_time = earliest.replace(hour=0, minute=0, second=0) + timedelta(days=1, seconds=random.randint(0, 30))
            frappe.db.sql("""
                INSERT INTO `tabActivity Log`
                (name, creation, modified, modified_by, owner, docstatus,
                 user, operation, status, full_name)
                VALUES (%s, %s, %s, 'Administrator', 'Administrator', 0, %s, 'Logout', 'Success', %s)
            """, (random_id(10), logout_time, logout_time, user_email, user_info["full_name"]))

            login_count += 1

    print(f"  Created {login_count} login/logout pairs.")

    # ── Step 5: Reassign existing Activity Log records ──────────
    print("\nReassigning existing Activity Log records by period...")
    for period in ACTIVITY_LOG_PERIODS:
        to_condition = f"AND creation < '{period['to']}'" if period["user"] != ACTIVITY_LOG_PERIODS[-1]["user"] else f"AND creation <= '{period['to']} 23:59:59'"
        frappe.db.sql(f"""
            UPDATE `tabActivity Log`
            SET user = '{period['user']}',
                owner = '{period['user']}',
                full_name = '{period['full_name']}'
            WHERE user = '{SOURCE_OWNER}'
              AND operation IN ('Login', 'Logout')
              AND creation >= '{period['from']}'
              {to_condition}
        """)
        print(f"  → {period['user']}: period {period['from']} to {period['to']}")

    frappe.db.commit()
    print("\n✅ All changes committed successfully.")
    print("=" * 60)

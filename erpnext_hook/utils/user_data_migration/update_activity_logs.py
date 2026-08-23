"""
Generate and update Activity Log entries for specified users.

Creates realistic Login / mid-day Session Expired + Re-Login / evening Logout
records based on when each user's Renovation Work Orders were created.
Also fills in all fields required for the Activity Log report (subject,
communication_date, ip_address) to match the format of active system users.

Usage:
    bench --site erp.almaidana.ae execute erpnext_hook.utils.user_data_migration.update_activity_logs.run
"""

import frappe
import random
import string
from datetime import timedelta
from collections import defaultdict


# ─────────────────────────────────────────────
# CONFIGURATION — Edit this section as needed
# ─────────────────────────────────────────────

USERS = [
    {
        "email":              "amani.bakheet@almaidana.ae",
        "full_name":          "Amani Bakheet",
        "primary_ip_prefix":  "87.200.",   # UAE Etisalat
    },
    {
        "email":              "hasna.ghanem@almaidana.ae",
        "full_name":          "Hasna Ghanem",
        "primary_ip_prefix":  "2.48.",     # UAE du
    },
    {
        "email":              "ameera.saad@almaidana.ae",
        "full_name":          "Ameera Saad",
        "primary_ip_prefix":  "94.205.",   # UAE Etisalat
    },
]

# Probability a day gets a mid-day session timeout + re-login (0.0 – 1.0)
MIDDAY_BREAK_PROBABILITY = 0.30

# Minimum daily work-order span (hours) that forces a mid-day break
MIDDAY_BREAK_MIN_SPAN_HOURS = 3.0

# Evening logout window in minutes past 17:00 (e.g. 5 – 80 → 17:05 – 18:20)
EVENING_LOGOUT_MIN_OFFSET_MINS = 5
EVENING_LOGOUT_MAX_OFFSET_MINS = 80

# ─────────────────────────────────────────────


UAE_IP_SUBNETS = [
    (2, 48), (2, 49), (2, 50),
    (5, 30), (5, 31),
    (5, 192), (5, 193),
    (87, 200), (87, 201),
    (94, 202), (94, 203), (94, 205),
    (80, 227),
    (217, 165),
    (109, 121),
]


def generate_uae_ip():
    subnet = random.choice(UAE_IP_SUBNETS)
    third = random.randint(1, 254)
    fourth = random.randint(2, 254)
    return f"{subnet[0]}.{subnet[1]}.{third}.{fourth}"


def chunk_list(lst, n=500):
    for i in range(0, len(lst), n):
        yield lst[i:i + n]


def random_id(length=10):
    return ''.join(random.choices(string.ascii_lowercase + string.digits, k=length))


def run():
    print("=" * 60)
    print("Starting Activity Log Generation")
    print("=" * 60)

    user_map = {u["email"]: u for u in USERS}
    user_emails = tuple(user_map.keys())

    # ── Step 1: Fetch all Work Orders for these users ───────────
    records = frappe.db.sql("""
        SELECT owner, creation, DATE(creation) as wo_date
        FROM `tabRenovation Work Order`
        WHERE owner IN %s
        ORDER BY creation
    """, (user_emails,), as_dict=True)

    print(f"\nLoaded {len(records)} Renovation Work Orders for timeline mapping.")

    user_daily_wos = defaultdict(lambda: defaultdict(list))
    for r in records:
        user_daily_wos[r.owner][str(r.wo_date)].append(r.creation)

    # ── Step 2: Clear previous Activity Log entries ─────────────
    print("\nClearing previous Activity Log entries for these users...")
    frappe.db.sql("DELETE FROM `tabActivity Log` WHERE user IN %s", (user_emails,))

    # ── Step 3: Generate structured records ────────────────────
    print("Generating structured Activity Log records...")
    activity_rows = []

    for user_email, daily in user_daily_wos.items():
        user_info = user_map[user_email]
        full_name = user_info["full_name"]

        # Generate a stable base IP for this user, with occasional alternates
        prefix = user_info["primary_ip_prefix"]
        parts = prefix.rstrip(".").split(".")
        base_ip = f"{parts[0]}.{parts[1]}.{random.randint(10, 250)}.{random.randint(2, 254)}"

        for date_str, timestamps in daily.items():
            if not timestamps:
                continue

            earliest_wo = min(timestamps)
            latest_wo   = max(timestamps)

            # IP for this day (90% stable, 10% alternate UAE IP)
            day_ip = base_ip if random.random() < 0.90 else generate_uae_ip()

            # ── Morning Login ──────────────────────────────────
            login_lead  = random.randint(5, 20)
            login_time  = earliest_wo - timedelta(minutes=login_lead, seconds=random.randint(0, 59))
            activity_rows.append(_login_row(random_id(), login_time, user_email, full_name, day_ip))

            # ── Optional Mid-day Timeout + Re-Login ───────────
            span_hours = (latest_wo - earliest_wo).total_seconds() / 3600.0
            has_break  = span_hours > MIDDAY_BREAK_MIN_SPAN_HOURS or random.random() < MIDDAY_BREAK_PROBABILITY

            if has_break:
                # Session Expired logout during lunch window
                break_hour = random.choice([12, 13])
                timeout_time = earliest_wo.replace(
                    hour=break_hour,
                    minute=random.randint(15, 45),
                    second=random.randint(0, 59),
                    microsecond=0
                )
                if timeout_time <= login_time:
                    timeout_time = login_time + timedelta(hours=2, minutes=random.randint(10, 40))
                activity_rows.append(_session_expired_row(random_id(), timeout_time, user_email, full_name))

                # Re-Login after break
                relogin_delay = random.randint(30, 75)
                relogin_time  = timeout_time + timedelta(minutes=relogin_delay, seconds=random.randint(0, 59))
                afternoon_wos = [t for t in timestamps if t > relogin_time]
                if afternoon_wos:
                    earliest_afternoon = min(afternoon_wos)
                    if relogin_time > earliest_afternoon - timedelta(minutes=5):
                        relogin_time = earliest_afternoon - timedelta(minutes=random.randint(5, 15))
                activity_rows.append(_login_row(random_id(), relogin_time, user_email, full_name, day_ip))

            # ── Evening Logout (always after 17:00) ───────────
            offset_mins     = random.randint(EVENING_LOGOUT_MIN_OFFSET_MINS, EVENING_LOGOUT_MAX_OFFSET_MINS)
            evening_base    = earliest_wo.replace(hour=17, minute=0, second=0, microsecond=0) + timedelta(minutes=offset_mins, seconds=random.randint(0, 59))
            post_last_wo    = latest_wo + timedelta(minutes=random.randint(10, 30), seconds=random.randint(0, 59))
            logout_time     = max(evening_base, post_last_wo)
            activity_rows.append(_manual_logout_row(random_id(), logout_time, user_email, full_name, day_ip))

    print(f"  Generated {len(activity_rows)} activity log entries.")

    # ── Step 4: Batch Insert ────────────────────────────────────
    print("\nInserting into tabActivity Log...")
    for chunk in chunk_list(activity_rows, 500):
        frappe.db.sql("""
            INSERT INTO `tabActivity Log`
            (name, creation, modified, modified_by, owner, docstatus,
             full_name, operation, reference_owner, subject,
             status, user, communication_date, ip_address)
            VALUES """ + ", ".join(["(%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)"] * len(chunk)),
            [val for row in chunk for val in row]
        )

    frappe.db.commit()
    print("\n✅ Activity Log records created and committed successfully.")
    print("=" * 60)


def _login_row(name, ts, user, full_name, ip):
    return (
        name, ts, ts, user, user, 0,
        full_name, "Login", "", f"{full_name} logged in",
        "Success", user, ts, ip
    )


def _session_expired_row(name, ts, user, full_name):
    return (
        name, ts, ts, "Administrator", "Administrator", 0,
        full_name, "Logout", "", f"{full_name} logged out: <strong>Session Expired</strong>",
        "Success", user, ts, None
    )


def _manual_logout_row(name, ts, user, full_name, ip):
    return (
        name, ts, ts, user, user, 0,
        full_name, "Logout", "", f"{full_name} logged out: <strong>User Manually Logged Out</strong>",
        "Success", user, ts, ip
    )

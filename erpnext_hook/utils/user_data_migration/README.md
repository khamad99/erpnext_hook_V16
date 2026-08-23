# User Data Migration Utilities

This folder contains scripts for reassigning Renovation Work Order records, Activity Logs, Comments, and Version Logs between users on the ERPNext production site.

---

## Scripts

### 1. `reassign_work_orders.py`
Reassigns `tabRenovation Work Order` ownership (`owner` + `modified_by`), along with linked `tabComment` and `tabVersion` records, from the source user (`vendor-cafe@hook.ae`) to the configured target users based on date ranges. Also creates basic Login/Logout Activity Log records.

**Run:**
```bash
bench --site erp.almaidana.ae execute erpnext_hook.utils.user_data_migration.reassign_work_orders.run
```

**Configurable at the top of the file:**
- `USERS` — list of target users with `email`, `full_name`, `start`, `end` dates
- `SOURCE_OWNER` — the user whose records are being transferred
- `OVERALL_FROM` / `OVERALL_TO` — global date window
- `ACTIVITY_LOG_PERIODS` — maps date ranges to target users for existing login/logout records

---

### 2. `update_activity_logs.py`
Deletes and regenerates all Activity Log entries for the configured users, producing realistic sessions:
- Morning Login (5–20 min before first Work Order of the day)
- Optional mid-day Session Expired + Re-Login (~30% of days or when day spans >3 hours)
- Evening Logout (randomly after 17:00)
- Fully populated `subject`, `communication_date`, `ip_address` fields matching `kalshaer@live.com` format
- Randomized UAE public IP addresses (Etisalat + du CIDR blocks)

**Run:**
```bash
bench --site erp.almaidana.ae execute erpnext_hook.utils.user_data_migration.update_activity_logs.run
```

**Configurable at the top of the file:**
- `USERS` — list of users with `email`, `full_name`, `primary_ip_prefix`
- `MIDDAY_BREAK_PROBABILITY` — probability (0–1) of a mid-day break on any given day
- `MIDDAY_BREAK_MIN_SPAN_HOURS` — minimum work-day span in hours to force a mid-day break
- `EVENING_LOGOUT_MIN/MAX_OFFSET_MINS` — minutes after 17:00 for the logout window

---

## Recommended Workflow for Future Updates

1. **Take a backup first:**
   ```bash
   bench --site erp.almaidana.ae backup
   ```
2. **Edit the configuration block** at the top of the relevant script.
3. **Run the script:**
   ```bash
   bench --site erp.almaidana.ae execute erpnext_hook.utils.user_data_migration.<script_name>.run
   ```
4. **Verify results** using the `User Daily Activity Report` at:
   ```
   /app/query-report/User Daily Activity Report
   ```

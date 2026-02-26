"""
BigTime API Explorer for GLE
Run this first to validate your API connection and see what data is available.
Usage: python bigtime_explorer.py

Requirements: pip install requests
"""

import requests
import json
from datetime import datetime, timedelta

# ─── CREDENTIALS ────────────────────────────────────────────────────────────
API_TOKEN = "Ctdcf3W+AFWeZU9VkamsnIjGNvMfI1gHzPCK9vUHNpXcAW883SdUT/Urvp+gI6lW"
FIRM_ID   = "akpf-qzjv-sgzv"
BASE_URL  = "https://iq.bigtime.net/BigtimeData/api/v2"

HEADERS = {
    "Content-Type":   "application/json",
    "Accept":         "application/json",
    "X-auth-ApiToken": API_TOKEN,
    "X-auth-realm":   FIRM_ID,
}

# ─── HELPERS ────────────────────────────────────────────────────────────────
def get(path, params=None):
    r = requests.get(f"{BASE_URL}{path}", headers=HEADERS, params=params, timeout=30)
    print(f"\n{'='*60}")
    print(f"GET {path}  →  {r.status_code}")
    if r.ok:
        data = r.json()
        print(json.dumps(data[:3] if isinstance(data, list) else data, indent=2, default=str))
        return data
    else:
        print(f"ERROR: {r.text[:500]}")
        return None

def post(path, body=None):
    r = requests.post(f"{BASE_URL}{path}", headers=HEADERS, json=body or {}, timeout=30)
    print(f"\n{'='*60}")
    print(f"POST {path}  →  {r.status_code}")
    if r.ok:
        data = r.json()
        print(json.dumps(data[:3] if isinstance(data, list) else data, indent=2, default=str))
        return data
    else:
        print(f"ERROR: {r.text[:500]}")
        return None

# ─── 1. AUTH TEST ────────────────────────────────────────────────────────────
print("\n" + "="*60)
print("STEP 1: FIRM-LEVEL AUTH TEST")
print("="*60)
auth = post("/session/firm")
if not auth:
    print("\n❌ Auth failed. Check your API token and Firm ID.")
    exit(1)
print("\n✅ Auth successful!")

# If session returns a token, use it
if isinstance(auth, dict) and auth.get("token"):
    HEADERS["X-auth-token"] = auth["token"]
    print(f"Session token acquired: {auth['token'][:20]}...")

# ─── 2. PROJECTS LIST ───────────────────────────────────────────────────────
print("\n" + "="*60)
print("STEP 2: ALL PROJECTS")
print("="*60)
projects = get("/project", params={"ShowInactive": "false"})

if projects and isinstance(projects, list):
    print(f"\n✅ Found {len(projects)} active projects")
    print("\nProject fields available:")
    if projects:
        print(list(projects[0].keys()))

# ─── 3. PROJECT DETAIL (first project) ─────────────────────────────────────
if projects and len(projects) > 0:
    first_id = projects[0].get("SID") or projects[0].get("Sid") or projects[0].get("sid")
    print(f"\n{'='*60}")
    print(f"STEP 3: PROJECT DETAIL (ID: {first_id})")
    print("="*60)
    detail = get(f"/project/detail/{first_id}", params={"View": "Detailed"})
    if detail:
        print(f"\nProject detail fields available:")
        if isinstance(detail, list):
            print(list(detail[0].keys()))
        else:
            print(list(detail.keys()))

# ─── 4. TASK BUDGET STATUS (first project) ──────────────────────────────────
if projects and len(projects) > 0:
    print(f"\n{'='*60}")
    print(f"STEP 4: TASK BUDGET STATUS (Project: {first_id})")
    print("="*60)
    budget = get(f"/task/BudgetStatusByProject/{first_id}")
    if budget:
        print(f"\n✅ Budget status fields available:")
        if isinstance(budget, list) and budget:
            print(list(budget[0].keys()))

# ─── 5. CLIENTS ─────────────────────────────────────────────────────────────
print(f"\n{'='*60}")
print("STEP 5: CLIENT LIST")
print("="*60)
clients = get("/client")
if clients and isinstance(clients, list):
    print(f"\n✅ Found {len(clients)} clients")
    if clients:
        print("Client fields:", list(clients[0].keys()))

# ─── 6. INVOICES (last 6 months) ────────────────────────────────────────────
print(f"\n{'='*60}")
print("STEP 6: RECENT INVOICES")
print("="*60)
start = (datetime.now() - timedelta(days=180)).strftime("%Y-%m-%d")
end   = datetime.now().strftime("%Y-%m-%d")
invoices = get("/invoice", params={"startDt": start, "endDt": end})
if invoices and isinstance(invoices, list):
    print(f"\n✅ Found {len(invoices)} invoices in last 6 months")
    if invoices:
        print("Invoice fields:", list(invoices[0].keys()))

# ─── 7. TIME ENTRIES (last 30 days, sample) ─────────────────────────────────
print(f"\n{'='*60}")
print("STEP 7: RECENT TIME ENTRIES (sample)")
print("="*60)
start30 = (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d")
time_entries = post("/time/reportbyfilter", {
    "mindate": start30,
    "maxdate": end,
    "view": "basic"
})
if time_entries and isinstance(time_entries, list):
    print(f"\n✅ Found {len(time_entries)} time entries in last 30 days")
    if time_entries:
        print("Time entry fields:", list(time_entries[0].keys()))

# ─── 8. EXPENSE ENTRIES (last 30 days) ──────────────────────────────────────
print(f"\n{'='*60}")
print("STEP 8: RECENT EXPENSES (sample)")
print("="*60)
expenses = post("/expense/reportbyfilter", {
    "mindate": start30,
    "maxdate": end,
    "view": "basic"
})
if expenses and isinstance(expenses, list):
    print(f"\n✅ Found {len(expenses)} expense entries in last 30 days")
    if expenses:
        print("Expense fields:", list(expenses[0].keys()))

# ─── 9. AVAILABLE REPORTS ───────────────────────────────────────────────────
print(f"\n{'='*60}")
print("STEP 9: AVAILABLE REPORTS IN BIGTIME")
print("="*60)
reports = get("/report")
if reports:
    print(f"\nReports available: {len(reports) if isinstance(reports, list) else 'see above'}")

# ─── 10. STAFF / COST RATES ─────────────────────────────────────────────────
print(f"\n{'='*60}")
print("STEP 10: STAFF LIST (for cost rates)")
print("="*60)
staff = get("/staff")
if staff and isinstance(staff, list):
    print(f"\n✅ Found {len(staff)} staff members")
    if staff:
        print("Staff fields:", list(staff[0].keys()))

print("\n" + "="*60)
print("EXPLORATION COMPLETE")
print("="*60)
print("\nNext steps:")
print("1. Share the output above so we can see which fields are populated")
print("2. We'll build the dashboard based on actual available data")
print("3. Key fields to confirm: bill rates, cost rates, invoice amounts, hours")

"""
BigTime Data Explorer for GLE - Auth confirmed working
Run: python bt_explore.py
"""
import requests
import json
from datetime import datetime, timedelta

API_TOKEN = "Ctdcf3W+AFWeZU9VkamsnnU5t9kEb+aKCl9E/B6KHAtZY7rhxn13fYEzVy6Iz9XV"
FIRM_ID   = "csuk-lqt-xwnw"
BASE_URL  = "https://iq.bigtime.net/BigtimeData/api/v2"

HEADERS = {
    "Accept":          "application/json",
    "Content-Type":    "application/json",
    "X-auth-ApiToken": API_TOKEN,
    "X-auth-realm":    FIRM_ID,
}

def get(path, params=None):
    r = requests.get(f"{BASE_URL}{path}", headers=HEADERS, params=params, timeout=30)
    print(f"\n{'='*60}\nGET {path} → {r.status_code}")
    if r.ok:
        data = r.json()
        sample = data[:2] if isinstance(data, list) else data
        print(json.dumps(sample, indent=2, default=str)[:1500])
        return data
    else:
        print(f"ERROR: {r.text[:300]}")
        return None

def post(path, body=None):
    r = requests.post(f"{BASE_URL}{path}", headers=HEADERS, json=body or {}, timeout=30)
    print(f"\n{'='*60}\nPOST {path} → {r.status_code}")
    if r.ok:
        data = r.json()
        sample = data[:2] if isinstance(data, list) else data
        print(json.dumps(sample, indent=2, default=str)[:1500])
        return data
    else:
        print(f"ERROR: {r.text[:300]}")
        return None

end   = datetime.now().strftime("%Y-%m-%d")
start = (datetime.now() - timedelta(days=180)).strftime("%Y-%m-%d")
start30 = (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d")

# 1. Projects
print("\n" + "="*60)
print("STEP 1: PROJECT LIST")
projects = get("/project", params={"ShowInactive": "false"})
if projects and isinstance(projects, list):
    print(f"\n✅ {len(projects)} active projects")
    print("Fields:", list(projects[0].keys()))

# 2. Project detail (first project)
if projects:
    pid = projects[0].get("SystemId") or projects[0].get("SID")
    print(f"\n{'='*60}\nSTEP 2: PROJECT DETAIL (ID: {pid})")
    detail = get(f"/project/detail/{pid}")
    if detail:
        fields = list(detail.keys()) if isinstance(detail, dict) else list(detail[0].keys())
        print("\nDetail fields:", fields)

# 3. Task budget status (first project)
if projects:
    print(f"\n{'='*60}\nSTEP 3: TASK BUDGET STATUS (Project: {pid})")
    budget = get(f"/task/BudgetStatusByProject/{pid}")
    if budget and isinstance(budget, list) and budget:
        print("\nBudget fields:", list(budget[0].keys()))

# 4. Clients
print(f"\n{'='*60}\nSTEP 4: CLIENTS")
clients = get("/client")
if clients and isinstance(clients, list):
    print(f"\n✅ {len(clients)} clients")
    print("Fields:", list(clients[0].keys()))

# 5. Invoices (last 6 months)
print(f"\n{'='*60}\nSTEP 5: INVOICES (last 6 months)")
invoices = get("/invoice", params={"startDt": start, "endDt": end})
if invoices and isinstance(invoices, list):
    print(f"\n✅ {len(invoices)} invoices")
    print("Fields:", list(invoices[0].keys()))

# 6. Time entries (last 30 days)
print(f"\n{'='*60}\nSTEP 6: TIME ENTRIES (last 30 days)")
time_entries = post("/time/reportbyfilter", {
    "mindate": start30,
    "maxdate": end,
    "view": "basic"
})
if time_entries and isinstance(time_entries, list):
    print(f"\n✅ {len(time_entries)} time entries")
    print("Fields:", list(time_entries[0].keys()))

# 7. Expenses (last 30 days)
print(f"\n{'='*60}\nSTEP 7: EXPENSES (last 30 days)")
expenses = post("/expense/reportbyfilter", {
    "mindate": start30,
    "maxdate": end,
    "view": "basic"
})
if expenses and isinstance(expenses, list):
    print(f"\n✅ {len(expenses)} expenses")
    print("Fields:", list(expenses[0].keys()))

# 8. Staff (for cost rates)
print(f"\n{'='*60}\nSTEP 8: STAFF")
staff = get("/staff")
if staff and isinstance(staff, list):
    print(f"\n✅ {len(staff)} staff members")
    print("Fields:", list(staff[0].keys()))
    # Check if cost rates are present
    sample = staff[0]
    cost_fields = [k for k in sample.keys() if "cost" in k.lower() or "rate" in k.lower() or "bill" in k.lower()]
    print("Rate/cost fields:", cost_fields)

# 9. Available reports
print(f"\n{'='*60}\nSTEP 9: AVAILABLE REPORTS")
reports = get("/report")
if reports and isinstance(reports, list):
    print(f"\n✅ {len(reports)} reports available")
    for r in reports[:10]:
        print(f"  - [{r.get('SID') or r.get('Id')}] {r.get('Nm') or r.get('Name') or r}")

print("\n" + "="*60)
print("EXPLORATION COMPLETE — paste all output back to Claude")
print("="*60)

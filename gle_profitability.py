"""
GLE Profitability Data Pull
Pulls all project profitability data and outputs to JSON for dashboard use.
Run: python gle_profitability.py
"""
import requests
import json
from datetime import datetime, timedelta
from collections import defaultdict

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
    if r.ok:
        return r.json()
    else:
        print(f"  ERROR {r.status_code} on GET {path}: {r.text[:200]}")
        return None

def post(path, body=None):
    r = requests.post(f"{BASE_URL}{path}", headers=HEADERS, json=body or {}, timeout=30)
    if r.ok:
        return r.json()
    else:
        print(f"  ERROR {r.status_code} on POST {path}: {r.text[:200]}")
        return None

# ── 1. Load supporting data ───────────────────────────────────────────────────
print("Loading staff (cost rates)...")
staff_list = get("/staff") or []
staff_map = {s["StaffSID"]: s for s in staff_list}
print(f"  {len(staff_map)} staff loaded")

print("Loading clients...")
clients_list = get("/client") or []
client_map = {c["SystemId"]: c for c in clients_list}
print(f"  {len(client_map)} clients loaded")

print("Loading projects...")
projects = get("/project", params={"ShowInactive": "false"}) or []
print(f"  {len(projects)} active projects loaded")

# Try to also get some inactive projects for historical data
all_projects = get("/project", params={"ShowInactive": "true"}) or projects
print(f"  {len(all_projects)} total projects (including inactive)")

# ── 2. Pull time entries for cost calculation ─────────────────────────────────
print("\nLoading time entries (last 365 days)...")
end_dt   = datetime.now().strftime("%Y-%m-%d")
start_dt = (datetime.now() - timedelta(days=365)).strftime("%Y-%m-%d")

# Try different endpoint formats for time
time_entries = []
# Try the list endpoint
te = get("/time/list", params={"StartDt": start_dt, "EndDt": end_dt})
if te and isinstance(te, list):
    time_entries = te
    print(f"  {len(time_entries)} time entries via /time/list")
else:
    # Try reportbyfilter with correct field names
    te2 = post("/time/reportbyfilter", {"StartDt": start_dt, "EndDt": end_dt, "View": "basic"})
    if te2 and isinstance(te2, list):
        time_entries = te2
        print(f"  {len(time_entries)} time entries via reportbyfilter")
    else:
        print("  Could not load time entries - will use FeeCostIn from task budget instead")

# ── 3. Pull expenses ──────────────────────────────────────────────────────────
print("\nLoading expenses (last 365 days)...")
expenses = post("/expense/reportbyfilter", {
    "mindate": start_dt,
    "maxdate": end_dt,
    "view": "basic"
}) or []
print(f"  {len(expenses)} expenses loaded")

# ── 4. Pull invoices ──────────────────────────────────────────────────────────
print("\nLoading invoices...")
invoices = []
# Try different invoice endpoint paths
for path, params in [
    ("/invoice/list", {"startDt": start_dt, "endDt": end_dt}),
    ("/invoice/list", {"StartDt": start_dt, "EndDt": end_dt}),
    ("/invoices", {"startDt": start_dt, "endDt": end_dt}),
]:
    inv = get(path, params)
    if inv and isinstance(inv, list):
        invoices = inv
        print(f"  {len(invoices)} invoices via {path}")
        print(f"  Invoice fields: {list(inv[0].keys()) if inv else 'n/a'}")
        break
else:
    print("  Could not load invoices - will use InvoicedToDate from task budget")

# ── 5. Core calculation: loop projects → get task budget status ───────────────
print(f"\nCalculating profitability for {len(projects)} projects...")
print("(This may take a minute due to API rate limits)\n")

project_results = []
client_totals = defaultdict(lambda: {
    "ClientId": 0, "ClientNm": "", "Revenue": 0, "LaborCost": 0,
    "ExpCost": 0, "TotalCost": 0, "Margin": 0, "MarginPct": 0,
    "HrsIn": 0, "Projects": []
})

import time as time_module

for i, proj in enumerate(projects):
    pid = proj["SystemId"]
    client_id = proj.get("ClientId", 0)
    client_nm = proj.get("DisplayName", "").split(":")[0] if ":" in proj.get("DisplayName", "") else proj.get("DisplayName", "Unknown Client")

    # Rate limit: 30 calls/min → pause briefly every 25 calls
    if i > 0 and i % 25 == 0:
        print(f"  ...{i}/{len(projects)} projects processed, pausing for rate limit...")
        time_module.sleep(3)

    # Get task budget status for this project
    tasks = get(f"/task/BudgetStatusByProject/{pid}") or []

    # Aggregate across tasks
    revenue       = sum(t.get("InvoicedToDate", 0) or 0 for t in tasks)
    labor_cost    = sum(t.get("FeeCostIn", 0) or 0 for t in tasks)
    exp_cost      = sum(t.get("ExpCostIn", 0) or 0 for t in tasks)
    wip           = sum(t.get("WipTotal", 0) or 0 for t in tasks)
    hrs_in        = sum(t.get("HrsIn", 0) or 0 for t in tasks)
    invoiced      = sum(t.get("InvoicedToDate", 0) or 0 for t in tasks)
    charge_in     = sum(t.get("ChargeIn", 0) or 0 for t in tasks)
    total_cost    = labor_cost + exp_cost
    margin        = revenue - total_cost
    margin_pct    = (margin / revenue * 100) if revenue > 0 else 0

    result = {
        "ProjectId":    pid,
        "ProjectNm":    proj.get("Nm", ""),
        "DisplayName":  proj.get("DisplayName", ""),
        "ProjectCode":  proj.get("ProjectCode", ""),
        "ClientId":     client_id,
        "ClientNm":     client_nm,
        "StartDt":      proj.get("StartDt", ""),
        "EndDt":        proj.get("EndDt", ""),
        "IsInactive":   proj.get("IsInactive", False),
        "BillingRate":  proj.get("BillingRate", ""),
        "BasicRate":    proj.get("BasicRate", 0),
        "BudgetHours":  proj.get("BudgetHours", 0),
        "BudgetFees":   proj.get("BudgetFees", 0),
        "HrsIn":        hrs_in,
        "ChargeIn":     charge_in,
        "LaborCost":    labor_cost,
        "ExpCost":      exp_cost,
        "TotalCost":    total_cost,
        "Revenue":      revenue,
        "WIP":          wip,
        "Margin":       margin,
        "MarginPct":    round(margin_pct, 1),
        "Tasks":        tasks,
        "TaskCount":    len(tasks),
    }
    project_results.append(result)

    # Roll up to client
    ct = client_totals[client_id]
    ct["ClientId"]  = client_id
    ct["ClientNm"]  = client_nm
    ct["Revenue"]   += revenue
    ct["LaborCost"] += labor_cost
    ct["ExpCost"]   += exp_cost
    ct["TotalCost"] += total_cost
    ct["HrsIn"]     += hrs_in
    ct["Projects"].append(pid)

# Compute client margins
for cid, ct in client_totals.items():
    ct["Margin"]    = ct["Revenue"] - ct["TotalCost"]
    ct["MarginPct"] = round(ct["Margin"] / ct["Revenue"] * 100, 1) if ct["Revenue"] > 0 else 0

# ── 6. Summary stats ──────────────────────────────────────────────────────────
total_revenue  = sum(p["Revenue"] for p in project_results)
total_cost     = sum(p["TotalCost"] for p in project_results)
total_margin   = total_revenue - total_cost
overall_margin = round(total_margin / total_revenue * 100, 1) if total_revenue > 0 else 0

print(f"\n{'='*60}")
print(f"SUMMARY")
print(f"{'='*60}")
print(f"Projects processed:  {len(project_results)}")
print(f"Total Revenue:       ${total_revenue:,.2f}")
print(f"Total Cost:          ${total_cost:,.2f}")
print(f"Total Margin:        ${total_margin:,.2f} ({overall_margin}%)")
print(f"Clients with data:   {len(client_totals)}")

# Top 10 by revenue
top_by_rev = sorted(project_results, key=lambda x: x["Revenue"], reverse=True)[:10]
print(f"\nTop 10 Projects by Revenue:")
for p in top_by_rev:
    print(f"  {p['ProjectCode']} {p['ProjectNm'][:40]:<40} Rev: ${p['Revenue']:>8,.0f}  Margin: {p['MarginPct']:>6.1f}%")

# Top 10 clients
top_clients = sorted(client_totals.values(), key=lambda x: x["Revenue"], reverse=True)[:10]
print(f"\nTop 10 Clients by Revenue:")
for c in top_clients:
    print(f"  {c['ClientNm'][:45]:<45} Rev: ${c['Revenue']:>8,.0f}  Margin: {c['MarginPct']:>6.1f}%")

# ── 7. Save output ────────────────────────────────────────────────────────────
output = {
    "generated":     datetime.now().isoformat(),
    "summary": {
        "total_revenue":  total_revenue,
        "total_cost":     total_cost,
        "total_margin":   total_margin,
        "overall_margin_pct": overall_margin,
        "project_count":  len(project_results),
        "client_count":   len(client_totals),
    },
    "projects":  project_results,
    "clients":   list(client_totals.values()),
    "staff":     staff_list,
}

with open("gle_profitability_data.json", "w") as f:
    json.dump(output, f, indent=2, default=str)

print(f"\n✅ Data saved to gle_profitability_data.json")
print("Next step: run the dashboard builder against this file")

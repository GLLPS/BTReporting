"""
Pull all GLE profitability data from BigTime and cache to gle_data.json.

Usage:
    python data_pull.py              # active projects only
    python data_pull.py --all        # include inactive projects
"""

import json
import sys
from collections import defaultdict
from datetime import datetime, timedelta

from bigtime_client import BigTimeClient


def pull_data(include_inactive=False):
    client = BigTimeClient()

    # ── 1. Supporting data ───────────────────────────────────────────────
    print("Loading staff...")
    staff_list = client.get_staff()
    staff_map = {s["StaffSID"]: s for s in staff_list}
    print(f"  {len(staff_list)} staff loaded")

    print("Loading clients...")
    clients_list = client.get_clients()
    client_map = {c["SystemId"]: c for c in clients_list}
    print(f"  {len(clients_list)} clients loaded")

    print("Loading projects...")
    projects = client.get_projects(active_only=not include_inactive)
    print(f"  {len(projects)} projects loaded")

    # ── 2. Project type picklist ───────────────────────────────────────────
    print("Loading project types...")
    type_list = client.get_project_types()
    type_map = {int(t["Id"]): t["Name"] for t in type_list}
    type_map[0] = "Unclassified"
    print(f"  {len(type_list)} project types loaded: {list(type_map.values())}")

    # ── 3. Expenses (last 365 days) ──────────────────────────────────────
    end_dt = datetime.now().strftime("%Y-%m-%d")
    start_dt = (datetime.now() - timedelta(days=365)).strftime("%Y-%m-%d")

    print("Loading expenses...")
    expenses = client.get_expenses(start_dt, end_dt)
    print(f"  {len(expenses)} expenses loaded")

    # Index expenses by project
    expense_by_project = defaultdict(list)
    for exp in expenses:
        expense_by_project[exp.get("ProjectSID", 0)].append(exp)

    # ── 4. Invoice history (last 3 years) ─────────────────────────────────
    inv_start = (datetime.now() - timedelta(days=1095)).strftime("%Y-%m-%d")
    print("Loading invoice history...")
    invoices = client.get_invoice_history(inv_start, end_dt)
    print(f"  {len(invoices)} invoices loaded")

    # Flatten invoices for storage (drop nested objects to keep JSON clean)
    invoice_results = []
    for inv in invoices:
        invoice_results.append({
            "InvoiceSid":    inv.get("Sid", 0),
            "InvoiceNbr":    inv.get("InvoiceNbr", ""),
            "InvoiceDt":     inv.get("InvoiceDt", ""),
            "InvoiceDtSent": inv.get("InvoiceDtSent", ""),
            "InvoiceDtDue":  inv.get("InvoiceDtDue", ""),
            "InvoicePeriod": inv.get("InvoicePeriod", 0),
            "ClientSid":     inv.get("ClientSid", 0),
            "ClientNm":      inv.get("ClientNm", ""),
            "ProjectSid":    inv.get("ProjectSid", 0),
            "DName":         inv.get("DName", ""),
            "InvoiceAmt":    inv.get("InvoiceAmt", 0),
            "Subtotal":      inv.get("Subtotal", 0),
            "SalesTaxAmt":   inv.get("SalesTaxAmt", 0),
            "TotalAmt":      inv.get("TotalAmt", 0),
            "PaidAmt":       inv.get("PaidAmt", 0),
            "TotalAmtDue":   inv.get("TotalAmtDue", 0),
            "IsPaid":        inv.get("IsPaid", False),
            "Status":        inv.get("Status", 0),
            "StatusTxt":     inv.get("StatusTxt", ""),
            "PostedStatus":  inv.get("PostedStatus", ""),
            "TermsNm":       inv.get("TermsNm", ""),
            "PONumber":      inv.get("PONumber", ""),
            "DaysOutstanding": inv.get("DaysOutstanding", 0),
            "ARPeriodNm":    inv.get("ARPeriodNm", ""),
        })

    # ── 5. Project profitability (task budget per project) ───────────────
    print(f"\nPulling task budgets for {len(projects)} projects...")
    project_results = []
    client_totals = defaultdict(lambda: {
        "ClientId": 0, "ClientNm": "",
        "Revenue": 0, "LaborCost": 0, "ExpCost": 0,
        "TotalCost": 0, "Margin": 0, "MarginPct": 0,
        "HrsIn": 0, "WIP": 0, "ProjectCount": 0,
    })

    for i, proj in enumerate(projects):
        pid = proj["SystemId"]
        display = proj.get("DisplayName", "")
        client_nm = display.split(":")[0] if ":" in display else display

        if (i + 1) % 25 == 0:
            print(f"  {i + 1}/{len(projects)} processed...")

        tasks = client.get_task_budget(pid)

        # Aggregate task-level numbers
        revenue    = sum(t.get("InvoicedToDate", 0) or 0 for t in tasks)
        labor_cost = sum(t.get("FeeCostIn", 0) or 0 for t in tasks)
        exp_cost   = sum(t.get("ExpCostIn", 0) or 0 for t in tasks)
        charge_in  = sum(t.get("ChargeIn", 0) or 0 for t in tasks)
        hrs_in     = sum(t.get("HrsIn", 0) or 0 for t in tasks)
        fee_wip    = sum(t.get("FeeWipToDate", 0) or 0 for t in tasks)
        exp_wip    = sum(t.get("ExpWipToDate", 0) or 0 for t in tasks)
        est_hrs    = sum(t.get("EstHrs", 0) or 0 for t in tasks)
        est_fee    = sum(t.get("EstFee", 0) or 0 for t in tasks)

        total_cost = labor_cost + exp_cost
        wip        = fee_wip + exp_wip
        margin     = revenue - total_cost
        margin_pct = round(margin / revenue * 100, 1) if revenue > 0 else 0.0

        type_id = proj.get("TypeId", 0) or 0
        type_name = type_map.get(type_id, f"Unknown ({type_id})")

        result = {
            "ProjectId":   pid,
            "DisplayName": display,
            "ProjectNm":   proj.get("Nm", ""),
            "ProjectCode": proj.get("ProjectCode", ""),
            "ClientId":    proj.get("ClientId", 0),
            "ClientNm":    client_nm,
            "TypeId":      type_id,
            "TypeName":    type_name,
            "BillingRate": proj.get("BillingRate", ""),
            "StartDt":     proj.get("StartDt", ""),
            "EndDt":       proj.get("EndDt", ""),
            "IsInactive":  proj.get("IsInactive", False),
            "BudgetHours": proj.get("BudgetHours", 0) or 0,
            "BudgetFees":  proj.get("BudgetFees", 0) or 0,
            "EstHrs":      est_hrs,
            "EstFee":      est_fee,
            "HrsIn":       hrs_in,
            "ChargeIn":    charge_in,
            "LaborCost":   labor_cost,
            "ExpCost":     exp_cost,
            "TotalCost":   total_cost,
            "Revenue":     revenue,
            "WIP":         wip,
            "FeeWIP":      fee_wip,
            "ExpWIP":      exp_wip,
            "Margin":      margin,
            "MarginPct":   margin_pct,
            "TaskCount":   len(tasks),
        }
        project_results.append(result)

        # Client rollup
        ct = client_totals[proj.get("ClientId", 0)]
        ct["ClientId"]  = proj.get("ClientId", 0)
        ct["ClientNm"]  = client_nm
        ct["Revenue"]   += revenue
        ct["LaborCost"] += labor_cost
        ct["ExpCost"]   += exp_cost
        ct["TotalCost"] += total_cost
        ct["HrsIn"]     += hrs_in
        ct["WIP"]       += wip
        ct["ProjectCount"] += 1

    # Compute client margins
    for ct in client_totals.values():
        ct["Margin"] = ct["Revenue"] - ct["TotalCost"]
        ct["MarginPct"] = round(ct["Margin"] / ct["Revenue"] * 100, 1) if ct["Revenue"] > 0 else 0.0

    # ── 6. Summary ───────────────────────────────────────────────────────
    total_revenue = sum(p["Revenue"] for p in project_results)
    total_cost    = sum(p["TotalCost"] for p in project_results)
    total_wip     = sum(p["WIP"] for p in project_results)
    total_margin  = total_revenue - total_cost
    overall_pct   = round(total_margin / total_revenue * 100, 1) if total_revenue > 0 else 0.0

    output = {
        "generated": datetime.now().isoformat(),
        "summary": {
            "total_revenue":      total_revenue,
            "total_cost":         total_cost,
            "total_margin":       total_margin,
            "overall_margin_pct": overall_pct,
            "total_wip":          total_wip,
            "project_count":      len(project_results),
            "client_count":       len(client_totals),
        },
        "project_types": type_map,
        "projects": project_results,
        "clients":  list(client_totals.values()),
        "staff":    staff_list,
        "expenses": expenses,
        "invoices": invoice_results,
    }

    with open("gle_data.json", "w") as f:
        json.dump(output, f, indent=2, default=str)

    print(f"\n{'='*55}")
    print(f"  Projects:  {len(project_results)}")
    print(f"  Invoices:  {len(invoice_results)}")
    print(f"  Revenue:   ${total_revenue:,.0f}")
    print(f"  Cost:      ${total_cost:,.0f}")
    print(f"  Margin:    ${total_margin:,.0f} ({overall_pct}%)")
    print(f"  WIP:       ${total_wip:,.0f}")
    print(f"{'='*55}")
    print("Saved to gle_data.json")


if __name__ == "__main__":
    pull_data(include_inactive="--all" in sys.argv)

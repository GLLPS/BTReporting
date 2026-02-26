"""
Probe newly discovered BigTime endpoints: invoice history + project type picklist.
"""
import json
from bigtime_client import BigTimeClient

client = BigTimeClient()

# ── 1. Invoice history ────────────────────────────────────────────────────────
print("=" * 60)
print("INVOICE HISTORY")
print("=" * 60)

invoices = client.get("/invoice/history", {
    "startDt": "2024-01-01",
    "endDt": "2026-12-31",
})
if invoices:
    n = len(invoices) if isinstance(invoices, list) else "dict"
    print(f"✅ Found {n} invoices!")
    if isinstance(invoices, list) and invoices:
        print(f"\nFields: {list(invoices[0].keys())}")
        print(f"\nFirst 3 invoices:")
        for inv in invoices[:3]:
            print(json.dumps(inv, indent=2, default=str))
else:
    print("❌ No invoice data returned")

# ── 2. Draft invoices ─────────────────────────────────────────────────────────
print(f"\n{'=' * 60}")
print("DRAFT INVOICES")
print("=" * 60)

drafts = client.get("/invoice/drafts")
if drafts:
    n = len(drafts) if isinstance(drafts, list) else "dict"
    print(f"✅ Found {n} drafts!")
    if isinstance(drafts, list) and drafts:
        print(f"\nFields: {list(drafts[0].keys())}")
else:
    print("❌ No draft data returned")

# ── 3. Project type picklist ──────────────────────────────────────────────────
print(f"\n{'=' * 60}")
print("PROJECT TYPE PICKLIST")
print("=" * 60)

picklist_names = [
    "LookupProjectType",
    "ProjectType",
    "LookupProjectGroup",
    "ProjectGroup",
    "LookupCategory",
    "Category",
]
for name in picklist_names:
    result = client.get(f"/picklist/FieldValues/{name}")
    if result is not None:
        n = len(result) if isinstance(result, list) else "dict"
        print(f"✅ /picklist/FieldValues/{name} → {n}")
        print(json.dumps(result[:10] if isinstance(result, list) else result, indent=2, default=str))

# ── 4. Project detail with Detailed view (for UdfList) ───────────────────────
print(f"\n{'=' * 60}")
print("PROJECT DETAIL (Detailed view - checking UdfList)")
print("=" * 60)

projects = client.get_projects(active_only=True)
if projects:
    pid = projects[0]["SystemId"]
    detail = client.get(f"/project/detail/{pid}", {"View": "Detailed"})
    if detail:
        d = detail[0] if isinstance(detail, list) else detail
        udf = d.get("UdfList")
        if udf:
            print(f"✅ UdfList found:")
            print(json.dumps(udf, indent=2, default=str))
        else:
            print("No UdfList field in response")
            # Check for any new fields
            known = {
                "BasicRate", "Billable", "BillingContactId", "BillingRate",
                "BudgetFees", "BudgetHours", "BudgetStyle", "Category",
                "ClientId", "CostCenterA", "CostCenterB", "CostCenterC",
                "CurrencySID", "DisplayName", "DtCreated", "DtModified",
                "EndDt", "InputFees", "InputHours", "InvoiceTotals",
                "InvoiceType", "IsAllStaff", "IsInactive", "IsNoCharge",
                "IsPto", "Nm", "Notes", "PrimaryContactId", "ProjectCode",
                "QBClassDefault", "StartDt", "StatusBill", "StatusProd",
                "StatusProd_nt", "SystemId", "TypeId",
            }
            new_fields = set(d.keys()) - known
            if new_fields:
                print(f"\nNew fields in Detailed view: {sorted(new_fields)}")
                for f in sorted(new_fields):
                    print(f"  {f} = {d.get(f)}")

# ── 5. Available reports ──────────────────────────────────────────────────────
print(f"\n{'=' * 60}")
print("AVAILABLE REPORTS")
print("=" * 60)

reports = client.get("/report")
if reports:
    if isinstance(reports, list):
        print(f"✅ {len(reports)} reports available")
        for r in reports[:10]:
            print(f"  {json.dumps(r, default=str)}")
    else:
        print(json.dumps(reports, indent=2, default=str)[:500])

print("\nDone!")

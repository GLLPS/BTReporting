"""
Probe BigTime API to resolve TypeId values to names.
"""
import json
from collections import Counter
from bigtime_client import BigTimeClient

client = BigTimeClient()
projects = client.get_projects(active_only=True)

# ── 1. Count projects per TypeId ──────────────────────────────────────────────
type_counts = Counter(p.get("TypeId", 0) for p in projects)
print("TypeId distribution:")
for tid, count in type_counts.most_common():
    sample = next(p["DisplayName"] for p in projects if p.get("TypeId") == tid)
    print(f"  TypeId={tid:>10}  ({count:>3} projects)  sample: {sample}")

# ── 2. Try to resolve TypeId via various endpoints ────────────────────────────
print(f"\n{'=' * 60}")
print("Trying to resolve TypeId to names...")
print("=" * 60)

type_endpoints = [
    "/project/type",
    "/project/types",
    "/projecttype",
    "/picklist/projecttype",
    "/picklist/PROJECTTYPE",
    "/picklist/ProjType",
    "/system/picklist/ProjectType",
    "/picklist?entity=project&field=TypeId",
]
for path in type_endpoints:
    result = client.get(path)
    if result is not None:
        print(f"  ✅ GET {path}")
        print(f"     Result: {json.dumps(result[:5] if isinstance(result, list) else result, indent=2, default=str)[:500]}")
        break

# ── 3. Try picklist with different entity names ──────────────────────────────
print(f"\n{'=' * 60}")
print("Trying various picklist endpoints...")
print("=" * 60)

picklist_names = [
    "ProjectType", "projecttype", "PROJECT_TYPE",
    "Type", "type", "ProjectGroup", "projectgroup",
    "Group", "group", "InvoiceType", "invoicetype",
    "StatusProd", "StatusBill", "BillingRate",
]
for name in picklist_names:
    result = client.get(f"/picklist/{name}")
    if result is not None:
        n = len(result) if isinstance(result, list) else "dict"
        print(f"  ✅ /picklist/{name} → {n}")
        if isinstance(result, list) and result:
            print(f"     Sample: {json.dumps(result[:3], indent=2, default=str)[:300]}")

# ── 4. Try the report endpoint with a project type report ────────────────────
print(f"\n{'=' * 60}")
print("Trying report endpoints...")
print("=" * 60)

report_endpoints = [
    "/report/project",
    "/report/Projects",
    "/report",
    "/reports",
]
for path in report_endpoints:
    result = client.get(path)
    if result is not None:
        n = len(result) if isinstance(result, list) else "dict"
        print(f"  ✅ GET {path} → {n}")
        if isinstance(result, list) and result:
            print(f"     Sample: {json.dumps(result[:3], indent=2, default=str)[:500]}")

# ── 5. Check if InvoiceTotals is useful ──────────────────────────────────────
print(f"\n{'=' * 60}")
print("InvoiceTotals field analysis:")
print("=" * 60)
for p in sorted(projects, key=lambda x: x.get("InvoiceTotals", 0), reverse=True)[:10]:
    print(f"  {p['DisplayName'][:50]:50s}  InvoiceTotals={p.get('InvoiceTotals', 0)}")

# ── 6. Try fetching invoice by project ────────────────────────────────────────
print(f"\n{'=' * 60}")
print("Trying project-specific invoice lookups...")
print("=" * 60)

pid = projects[0]["SystemId"]
inv_paths = [
    f"/project/{pid}/invoices",
    f"/project/{pid}/invoice",
    f"/invoice/project/{pid}",
]
for path in inv_paths:
    result = client.get(path)
    if result is not None:
        n = len(result) if isinstance(result, list) else "dict"
        print(f"  ✅ GET {path} → {n}")
        if isinstance(result, list) and result:
            print(f"     Fields: {list(result[0].keys())}")
            print(f"     Sample: {json.dumps(result[0], indent=2, default=str)[:500]}")

print("\nDone.")

"""
Probe BigTime API to discover project classification fields and invoice endpoints.
Usage: python bt_probe.py
"""

import json
from bigtime_client import BigTimeClient

client = BigTimeClient()

# ── 1. Get ALL fields from first 3 projects ──────────────────────────────────
print("=" * 60)
print("STEP 1: Full project field dump (first 3 projects)")
print("=" * 60)

projects = client.get_projects(active_only=True)
print(f"\n{len(projects)} active projects found")

if projects:
    print(f"\nAll fields on project[0]:")
    for k, v in sorted(projects[0].items()):
        print(f"  {k:30s} = {v}")

    # Show all unique values for likely classification fields
    possible_type_fields = [
        "Group", "ProjectGroup", "ProjectType", "Type", "Category",
        "Classification", "Sector", "Division", "Department",
        "BillingType", "BillingRate", "StatusProd", "StatusBill",
        "ContractType", "ServiceType", "ProjType", "ProjGroup",
        "CustomField1", "CustomField2", "CustomField3",
        "CF1", "CF2", "CF3", "UDF1", "UDF2", "UDF3",
        "Grp", "GrpNm", "GroupNm",
    ]

    print(f"\n{'=' * 60}")
    print("STEP 2: Checking potential classification fields")
    print("=" * 60)

    for field in possible_type_fields:
        vals = set()
        for p in projects:
            v = p.get(field)
            if v is not None and v != "" and v != 0:
                vals.add(str(v))
        if vals:
            print(f"\n  FOUND: {field}")
            print(f"    Unique values ({len(vals)}): {sorted(vals)[:20]}")

    # Also check for any field containing "type", "group", "class", "cat"
    print(f"\n{'=' * 60}")
    print("STEP 3: Fields containing 'type', 'group', 'class', 'cat' in name")
    print("=" * 60)

    for k in sorted(projects[0].keys()):
        kl = k.lower()
        if any(x in kl for x in ["type", "group", "class", "cat", "sector", "division", "custom", "udf"]):
            vals = set(str(p.get(k, "")) for p in projects if p.get(k))
            print(f"  {k:30s} → {len(vals)} unique values: {sorted(vals)[:10]}")

# ── 2. Get project detail for more fields ─────────────────────────────────────
if projects:
    pid = projects[0]["SystemId"]
    print(f"\n{'=' * 60}")
    print(f"STEP 4: Project detail for ID {pid}")
    print("=" * 60)
    detail = client.get_project_detail(pid)
    if detail:
        d = detail[0] if isinstance(detail, list) else detail
        print(f"\nAll fields on project detail:")
        for k, v in sorted(d.items()):
            print(f"  {k:30s} = {v}")

        # Extra fields in detail not in list?
        list_keys = set(projects[0].keys())
        detail_keys = set(d.keys())
        extra = detail_keys - list_keys
        if extra:
            print(f"\n  Extra fields in detail (not in list): {sorted(extra)}")
        else:
            print(f"\n  No extra fields in detail vs list")

# ── 3. Try invoice endpoints ──────────────────────────────────────────────────
print(f"\n{'=' * 60}")
print("STEP 5: Probing invoice endpoints")
print("=" * 60)

invoice_paths = [
    "/invoice",
    "/invoices",
    "/invoice/list",
    "/billing/invoice",
    "/billing/invoices",
    "/billing",
    "/report/invoice",
    "/invoice/reportbyfilter",
    "/picklist/invoice",
    "/invoice/search",
]

for path in invoice_paths:
    result = client.get(path)
    if result is not None:
        n = len(result) if isinstance(result, list) else "dict"
        print(f"  ✅ GET {path} → {n} results")
        if isinstance(result, list) and result:
            print(f"     Fields: {list(result[0].keys())}")
            print(f"     Sample: {json.dumps(result[0], indent=2, default=str)[:500]}")
        elif isinstance(result, dict):
            print(f"     Keys: {list(result.keys())}")
        break  # Found it

# Also try POST variants
post_paths = [
    "/invoice/reportbyfilter",
    "/billing/reportbyfilter",
]
for path in post_paths:
    result = client.post(path, {"mindate": "2024-01-01", "maxdate": "2025-12-31", "view": "basic"})
    if result is not None:
        n = len(result) if isinstance(result, list) else "dict"
        print(f"  ✅ POST {path} → {n} results")
        if isinstance(result, list) and result:
            print(f"     Fields: {list(result[0].keys())}")
            print(f"     Sample: {json.dumps(result[0], indent=2, default=str)[:500]}")
        break

# ── 4. Try to get picklists (often have project types/groups) ──────────────
print(f"\n{'=' * 60}")
print("STEP 6: Probing picklists for project types/groups")
print("=" * 60)

picklist_paths = [
    "/picklist/ProjectType",
    "/picklist/ProjectGroup",
    "/picklist/Group",
    "/picklist",
]
for path in picklist_paths:
    result = client.get(path)
    if result is not None:
        n = len(result) if isinstance(result, list) else "dict"
        print(f"  ✅ GET {path} → {n} results")
        if isinstance(result, list) and result:
            print(f"     Sample: {json.dumps(result[:5], indent=2, default=str)}")

print("\n" + "=" * 60)
print("PROBE COMPLETE")
print("=" * 60)

"""
Probe invoice detail to see line item / service item structure.
"""
import json
from bigtime_client import BigTimeClient

client = BigTimeClient()

# Get a few invoices to inspect their line items
invoices = client.get_invoice_history("2025-01-01", "2026-02-28")
print(f"{len(invoices)} invoices in range")

# Pick a few with different amounts to see variety
samples = invoices[:5]

for inv in samples:
    sid = inv["Sid"]
    print(f"\n{'='*60}")
    print(f"Invoice #{inv['InvoiceNbr']} — {inv['ClientNm']} — ${inv['InvoiceAmt']:,.2f}")
    print(f"Project: {inv['DName']}")
    print(f"Date: {inv['InvoiceDt']}")
    print("="*60)

    detail = client.get(f"/invoice/detail/{sid}")
    if detail:
        d = detail if isinstance(detail, dict) else detail[0]
        lines = d.get("Lines", [])
        print(f"  {len(lines)} line items:")
        for line in lines:
            print(f"    Line {line.get('LineNbr')}: {line.get('Nm', '???')}")
            print(f"      Qty={line.get('Quantity')}  Rate=${line.get('Rate')}  Amt=${line.get('Amt')}")
            print(f"      LineType={line.get('LineType')}  Source={line.get('Source')}")
            print(f"      ProjectSid={line.get('ProjectSid')}  AcctSid={line.get('AcctSid')}")
            print(f"      Note={line.get('Nt', '')[:100]}")
            # Print ALL fields on first line to see what's available
            if line.get("LineNbr") == 1:
                print(f"      ALL FIELDS: {list(line.keys())}")

# Also check task budget to see if task names map to service items
print(f"\n{'='*60}")
print("TASK BUDGET SAMPLE (first project)")
print("="*60)
projects = client.get_projects(active_only=True)
if projects:
    pid = projects[0]["SystemId"]
    tasks = client.get_task_budget(pid)
    print(f"Project: {projects[0]['DisplayName']}")
    print(f"{len(tasks)} tasks:")
    for t in tasks[:5]:
        print(f"  Task: {t.get('Nm', t.get('TaskNm', '???'))}")
        print(f"    HrsIn={t.get('HrsIn')}  FeeCostIn={t.get('FeeCostIn')}  InvoicedToDate={t.get('InvoicedToDate')}")
        print(f"    ALL FIELDS: {list(t.keys())}")

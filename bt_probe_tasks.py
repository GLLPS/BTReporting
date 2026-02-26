"""
Probe task names and groups across projects to understand service item structure.
"""
import json
from collections import Counter
from bigtime_client import BigTimeClient

client = BigTimeClient()
projects = client.get_projects(active_only=True)

# Load project types
type_list = client.get_project_types()
type_map = {int(t["Id"]): t["Name"] for t in type_list}
type_map[0] = "Unclassified"

all_tasks = []
task_names = Counter()
task_groups = Counter()

print(f"Pulling tasks for {len(projects)} projects...")
for i, proj in enumerate(projects):
    pid = proj["SystemId"]
    type_name = type_map.get(proj.get("TypeId", 0), "Unknown")

    tasks = client.get_task_budget(pid)
    for t in tasks:
        tn = t.get("TaskNm", "")
        tg = t.get("TaskGroup", "")
        task_names[tn] += 1
        if tg:
            task_groups[tg] += 1
        all_tasks.append({
            "Project": proj.get("DisplayName", ""),
            "TypeName": type_name,
            "TaskNm": tn,
            "TaskGroup": tg,
            "HrsIn": t.get("HrsIn", 0),
            "FeeCostIn": t.get("FeeCostIn", 0),
            "ExpCostIn": t.get("ExpCostIn", 0),
            "InvoicedToDate": t.get("InvoicedToDate", 0),
            "ChargeIn": t.get("ChargeIn", 0),
        })

    if (i + 1) % 25 == 0:
        print(f"  {i+1}/{len(projects)}...")

print(f"\n{'='*60}")
print(f"TOTAL TASKS: {len(all_tasks)}")
print(f"\n{'='*60}")
print(f"UNIQUE TASK NAMES ({len(task_names)}):")
for name, count in task_names.most_common():
    print(f"  {count:>4}x  {name}")

print(f"\n{'='*60}")
print(f"UNIQUE TASK GROUPS ({len(task_groups)}):")
for name, count in task_groups.most_common():
    print(f"  {count:>4}x  {name}")

# Show a few multi-task projects
print(f"\n{'='*60}")
print("SAMPLE MULTI-TASK PROJECTS:")
from collections import defaultdict
proj_tasks = defaultdict(list)
for t in all_tasks:
    proj_tasks[t["Project"]].append(t)

multi = [(p, ts) for p, ts in proj_tasks.items() if len(ts) > 1]
for proj, tasks in sorted(multi, key=lambda x: -len(x[1]))[:10]:
    print(f"\n  {proj} ({tasks[0]['TypeName']}) — {len(tasks)} tasks:")
    for t in tasks:
        inv = t["InvoicedToDate"] or 0
        cost = (t["FeeCostIn"] or 0) + (t["ExpCostIn"] or 0)
        print(f"    {t['TaskNm']:40s}  Hrs={t['HrsIn']:>6.1f}  Invoiced=${inv:>10,.0f}  Cost=${cost:>10,.0f}")

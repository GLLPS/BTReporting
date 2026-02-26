"""
Natural language query engine for BigTime reporting data.

Translates plain-English questions into Pandas operations using the Anthropic API.
Falls back to keyword-based parsing if no API key is configured.
"""

import json
import os
import re
from pathlib import Path

import pandas as pd
from dotenv import dotenv_values

_ENV_PATH = Path(__file__).resolve().parent / ".env"
_cfg = dotenv_values(_ENV_PATH, encoding="utf-8-sig")

# ── Schema descriptions for the LLM prompt ───────────────────────────────────

PROJECT_COLUMNS = {
    "ProjectId":   "Unique project ID",
    "DisplayName": "Full name (Client:Project)",
    "ProjectNm":   "Project name only",
    "ProjectCode": "Project code number",
    "ClientNm":    "Client name",
    "TypeName":    "Project classification (e.g. GI CSA, Safety, Enviro Project, IH, Construction Safety, Construction CSA, SSR Construction, SSR Environmental, ICR 59, Expert Witness, Unclassified)",
    "BillingRate": "Billing type (flat or staffA/T&M)",
    "StartDt":     "Project start date (YYYY-MM-DD)",
    "EndDt":       "Project end date (YYYY-MM-DD)",
    "HrsIn":       "Total hours logged",
    "ChargeIn":    "Billable value of hours",
    "Revenue":     "Total amount invoiced to date ($)",
    "LaborCost":   "Total labor cost ($)",
    "ExpCost":     "Total expense/other cost ($)",
    "TotalCost":   "Total cost (labor + expense) ($)",
    "Margin":      "Profit in dollars (Revenue - TotalCost)",
    "MarginPct":   "Profit margin percentage",
    "WIP":         "Work in progress (unbilled) ($)",
    "BudgetHours": "Budgeted hours",
    "BudgetFees":  "Budgeted fees ($)",
    "TaskCount":   "Number of tasks in project",
}

INVOICE_COLUMNS = {
    "InvoiceSid":    "Unique invoice ID",
    "InvoiceNbr":    "Invoice number",
    "InvoiceDt":     "Invoice date (YYYY-MM-DD)",
    "InvoiceDtSent": "Date invoice was sent (YYYY-MM-DD)",
    "InvoiceDtDue":  "Invoice due date (YYYY-MM-DD)",
    "InvoicePeriod": "Invoice period (YYYYMM integer)",
    "ClientSid":     "Client ID",
    "ClientNm":      "Client name",
    "ProjectSid":    "Project ID",
    "DName":         "Display name (Client:Project)",
    "InvoiceAmt":    "Invoice amount ($)",
    "TotalAmt":      "Total amount including tax ($)",
    "PaidAmt":       "Amount paid ($)",
    "TotalAmtDue":   "Amount still due ($)",
    "IsPaid":        "Whether invoice is fully paid (true/false)",
    "StatusTxt":     "Invoice status (Draft, Posted, etc.)",
    "TermsNm":       "Payment terms (e.g. Net 30)",
    "PONumber":      "Purchase order number",
    "DaysOutstanding": "Days since invoice was sent",
    "ARPeriodNm":    "Aging period (Current, 30 days, 60 days, etc.)",
}

SYSTEM_PROMPT = """You are a data query assistant for a project profitability dashboard.
You translate plain-English questions into a JSON query specification.

Available data tables:
1. "projects" — one row per project with profitability metrics
2. "invoices" — one row per invoice with dates and amounts

PROJECT COLUMNS:
{project_cols}

INVOICE COLUMNS:
{invoice_cols}

AVAILABLE PROJECT TYPES: {project_types}

RULES:
- Output ONLY valid JSON, no explanation text
- The JSON must have this structure:
{{
  "table": "projects" or "invoices" or "combined",
  "filters": [
    {{"column": "col_name", "op": "eq|ne|gt|lt|gte|lte|in|contains|between|year", "value": ...}}
  ],
  "columns": ["col1", "col2", ...],
  "sort_by": "col_name" or null,
  "sort_asc": true or false,
  "group_by": "col_name" or null,
  "agg": {{"col": "sum|mean|count|min|max"}} or null,
  "limit": number or null,
  "title": "Short description of this report"
}}

- For "combined" table: filters on invoice fields AND project fields. The join is on ProjectSid=ProjectId.
- For year filtering on dates, use op="year" with value=2025 (the engine extracts the year).
- For "in" operator, value should be a list: ["GI CSA", "Safety"]
- For "between" operator, value should be [min, max]
- "contains" does case-insensitive substring match
- When user says "invoiced in 2025" use table="invoices" with filter on InvoiceDt year=2025
- When user asks for "profit" use the "Margin" column
- When user asks for "other cost" or "non-labor cost" use "ExpCost"
- When user asks for "total invoiced" or "amount invoiced" use "InvoiceAmt" (from invoices) or "Revenue" (from projects)
- Always include a descriptive "title" field
"""


def _build_system_prompt(project_types):
    """Build the system prompt with actual column info and project types."""
    pcols = "\n".join(f"  - {k}: {v}" for k, v in PROJECT_COLUMNS.items())
    icols = "\n".join(f"  - {k}: {v}" for k, v in INVOICE_COLUMNS.items())
    types_str = ", ".join(sorted(project_types)) if project_types else "unknown"
    return SYSTEM_PROMPT.format(
        project_cols=pcols,
        invoice_cols=icols,
        project_types=types_str,
    )


def query_with_llm(question, project_types, api_key=None):
    """Use Anthropic Claude API to parse a natural language question into a query spec."""
    key = api_key or _cfg.get("ANTHROPIC_API_KEY") or os.environ.get("ANTHROPIC_API_KEY")
    if not key:
        return None, "No ANTHROPIC_API_KEY found in .env. Add it to enable natural language queries."

    try:
        import anthropic
    except ImportError:
        return None, "anthropic package not installed. Run: pip install anthropic"

    client = anthropic.Anthropic(api_key=key)
    system = _build_system_prompt(project_types)

    msg = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=1024,
        system=system,
        messages=[{"role": "user", "content": question}],
    )

    text = msg.content[0].text.strip()
    # Extract JSON from possible markdown code blocks
    json_match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.DOTALL)
    if json_match:
        text = json_match.group(1)

    try:
        spec = json.loads(text)
        return spec, None
    except json.JSONDecodeError as e:
        return None, f"Failed to parse LLM response as JSON: {e}\nRaw: {text[:500]}"


def execute_query(spec, df_projects, df_invoices):
    """Execute a query spec against the DataFrames. Returns (result_df, title, error)."""
    try:
        table = spec.get("table", "projects")
        title = spec.get("title", "Query Results")

        # Pick the base DataFrame
        if table == "projects":
            df = df_projects.copy()
        elif table == "invoices":
            df = df_invoices.copy()
        elif table == "combined":
            # Join invoices with project data (exclude columns already in invoices)
            proj_cols_to_join = [c for c in df_projects.columns if c not in df_invoices.columns]
            if "ProjectId" not in proj_cols_to_join:
                proj_cols_to_join.append("ProjectId")
            df = df_invoices.merge(
                df_projects[proj_cols_to_join].drop_duplicates(subset=["ProjectId"]),
                left_on="ProjectSid",
                right_on="ProjectId",
                how="left",
            )
        else:
            return None, title, f"Unknown table: {table}"

        # Apply filters
        for filt in spec.get("filters", []):
            col = filt["column"]
            op = filt["op"]
            val = filt["value"]

            if col not in df.columns:
                continue

            if op == "eq":
                df = df[df[col] == val]
            elif op == "ne":
                df = df[df[col] != val]
            elif op == "gt":
                df = df[df[col] > val]
            elif op == "lt":
                df = df[df[col] < val]
            elif op == "gte":
                df = df[df[col] >= val]
            elif op == "lte":
                df = df[df[col] <= val]
            elif op == "in":
                df = df[df[col].isin(val)]
            elif op == "contains":
                df = df[df[col].astype(str).str.contains(val, case=False, na=False)]
            elif op == "between":
                df = df[df[col].between(val[0], val[1])]
            elif op == "year":
                date_col = pd.to_datetime(df[col], errors="coerce")
                df = df[date_col.dt.year == val]

        # Group by + aggregate
        group_by = spec.get("group_by")
        agg = spec.get("agg")
        if group_by and agg and group_by in df.columns:
            agg_funcs = {}
            for acol, afunc in agg.items():
                if acol in df.columns:
                    agg_funcs[acol] = afunc
            if agg_funcs:
                df = df.groupby(group_by).agg(agg_funcs).reset_index()

        # Select columns
        columns = spec.get("columns")
        if columns:
            available = [c for c in columns if c in df.columns]
            if available:
                df = df[available]

        # Sort
        sort_by = spec.get("sort_by")
        if sort_by and sort_by in df.columns:
            df = df.sort_values(sort_by, ascending=spec.get("sort_asc", True))

        # Limit
        limit = spec.get("limit")
        if limit:
            df = df.head(limit)

        return df, title, None

    except Exception as e:
        return None, spec.get("title", "Query Results"), str(e)


def keyword_parse(question, project_types):
    """Simple keyword-based parser as fallback when no API key is available."""
    q = question.lower()
    spec = {
        "table": "projects",
        "filters": [],
        "columns": None,
        "sort_by": None,
        "sort_asc": True,
        "group_by": None,
        "agg": None,
        "limit": None,
        "title": question,
    }

    # Detect if asking about invoices
    if any(w in q for w in ["invoice", "invoiced", "billing", "billed", "paid", "unpaid", "outstanding", "ar ", "aging"]):
        spec["table"] = "invoices"

    # Detect project type filters
    for type_name in (project_types or []):
        if type_name.lower() in q:
            if spec["table"] == "invoices":
                spec["table"] = "combined"
            spec["filters"].append({"column": "TypeName", "op": "eq", "value": type_name})
            break

    # Detect year filters
    year_match = re.search(r"\b(202[0-9])\b", q)
    if year_match:
        year = int(year_match.group(1))
        if spec["table"] in ("invoices", "combined"):
            spec["filters"].append({"column": "InvoiceDt", "op": "year", "value": year})
        else:
            spec["filters"].append({"column": "StartDt", "op": "year", "value": year})

    # Detect client name
    client_match = re.search(r"(?:for|from|client)\s+[\"']?([A-Z][a-zA-Z\s&.,]+)", question)
    if client_match:
        spec["filters"].append({"column": "ClientNm", "op": "contains", "value": client_match.group(1).strip()})

    # Detect column requests
    col_keywords = {
        "client name": "ClientNm",
        "project name": "ProjectNm",
        "project type": "TypeName",
        "type": "TypeName",
        "hours": "HrsIn",
        "total hours": "HrsIn",
        "revenue": "Revenue",
        "invoiced": "Revenue",
        "amount invoiced": "Revenue",
        "total invoiced": "Revenue",
        "labor cost": "LaborCost",
        "labour cost": "LaborCost",
        "other cost": "ExpCost",
        "expense cost": "ExpCost",
        "total cost": "TotalCost",
        "profit": "Margin",
        "margin": "Margin",
        "margin %": "MarginPct",
        "margin percent": "MarginPct",
        "wip": "WIP",
    }
    detected_cols = []
    for keyword, col in col_keywords.items():
        if keyword in q and col not in detected_cols:
            detected_cols.append(col)

    if detected_cols:
        spec["columns"] = detected_cols

    # Detect sorting
    if "top" in q or "highest" in q or "most" in q:
        spec["sort_asc"] = False
        if "profit" in q or "margin" in q:
            spec["sort_by"] = "Margin"
        elif "revenue" in q or "invoiced" in q:
            spec["sort_by"] = "Revenue"
        elif "hours" in q:
            spec["sort_by"] = "HrsIn"

    if "bottom" in q or "lowest" in q or "least" in q:
        spec["sort_asc"] = True
        if "profit" in q or "margin" in q:
            spec["sort_by"] = "Margin"
        elif "revenue" in q or "invoiced" in q:
            spec["sort_by"] = "Revenue"

    # Detect limit
    limit_match = re.search(r"(?:top|bottom|first|last)\s+(\d+)", q)
    if limit_match:
        spec["limit"] = int(limit_match.group(1))

    # Detect unpaid
    if "unpaid" in q or "outstanding" in q:
        spec["filters"].append({"column": "IsPaid", "op": "eq", "value": False})

    return spec

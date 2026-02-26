# GLE BigTime Profitability Dashboard — Claude Code Handoff

## Project Goal
Build a local profitability dashboard for Great Lakes Environmental & Safety Consultants (GLE) pulling live data from the BigTime API. Target metrics: project-level profitability, client-level rollups, margin %, WIP, hours vs. budget.

---

## BigTime API — Authentication (SOLVED)

**What works:**
```python
HEADERS = {
    "Accept":          "application/json",
    "Content-Type":    "application/json",
    "X-auth-ApiToken": API_TOKEN,   # firm-level key, permanent
    "X-auth-realm":    FIRM_ID,     # either slug or tenant ID both work
}
```

**Credentials (store in .env, never commit):**
```
BIGTIME_API_TOKEN=Ctdcf3W+AFWeZU9VkamsnnU5t9kEb+aKCl9E/B6KHAtZY7rhxn13fYEzVy6Iz9XV
BIGTIME_FIRM_ID=csuk-lqt-xwnw
BIGTIME_TENANT_ID=17982
BIGTIME_BASE_URL=https://iq.bigtime.net/BigtimeData/api/v2
```

**What does NOT work:**
- `POST /session` with username/password — account uses a different auth mechanism
- `POST /session/firm` with token in body — returns 403
- The firm-level API key works directly in headers without any session exchange

**Rate limit:** 30 calls/minute per token. Built-in pause every 25 calls.

---

## API Endpoints — Confirmed Working

| Endpoint | Method | Notes |
|---|---|---|
| `/project` | GET | `?ShowInactive=false/true`. Returns 174 active projects. |
| `/project/detail/{id}` | GET | Same fields as list, no extra detail fields found |
| `/task/BudgetStatusByProject/{projectId}` | GET | **Key profitability endpoint** |
| `/client` | GET | 610 clients total |
| `/staff` | GET | 11 staff, includes cost rates |
| `/expense/reportbyfilter` | POST | Body: `{mindate, maxdate, view: "basic"}` |

**Endpoints that returned 404 (need investigation):**
- `/invoice` — wrong path, correct path unknown
- `/invoice/list` — also 404
- `/report` — may not be enabled for firm-level tokens
- `/time/reportbyfilter` — returns 400, field names unclear

---

## Data Available — Key Fields

### Projects (`/project`)
- `SystemId` — project ID (use for task budget lookup)
- `ClientId` — links to client
- `DisplayName` — format is "Client Name:Project Name"
- `BillingRate`, `BasicRate` — billing rate type and base rate
- `BudgetHours`, `BudgetFees` — budget targets
- `IsInactive`, `StatusProd`, `StatusBill`

### Task Budget Status (`/task/BudgetStatusByProject/{id}`)
**This is the core profitability data source:**
- `FeeCostIn` — labor cost (hours × staff cost rate, calculated by BigTime)
- `InvoicedToDate` — revenue billed to date
- `ChargeIn` — billable value of hours logged
- `HrsIn` — hours logged
- `ExpCostIn` — expense cost
- `ExpWipToDate` — unbilled expense WIP
- `FeeWipToDate` — unbilled fee WIP
- `EstHrs`, `EstFee` — budget estimates
- `RemainingEstHrs`, `RemainingEstFee` — budget remaining

**Profitability formula:**
```
Revenue     = InvoicedToDate
Labor Cost  = FeeCostIn
Exp Cost    = ExpCostIn
Total Cost  = FeeCostIn + ExpCostIn
Margin $    = Revenue - Total Cost
Margin %    = Margin / Revenue * 100
WIP         = WipTotal (unbilled work in progress)
```

### Staff (`/staff`)
- `StaffSID`, `FullName`, `Title`
- `CostFactor` — hourly cost rate (e.g., Colin Casey = $113.54/hr) ✅ populated
- `Rate1` through `Rate5` — billing rates
- `Capacity` — monthly hour capacity

### Expenses (`/expense/reportbyfilter`)
- `ProjectSID`, `ClientSID`, `ClientNm`
- `CostIN` — actual cost
- `CostBill` — billable amount
- `Dt`, `CatNm`, `Nt` (notes)
- `IsSubmitted`, `PaidByCo`

---

## Recommended Architecture

```
BTReporting/
├── .env                    # credentials (gitignored)
├── .gitignore
├── requirements.txt
├── bigtime_client.py       # API wrapper class with rate limiting
├── data_pull.py            # pulls all data → gle_data.json
├── dashboard.py            # Streamlit or Dash dashboard
└── gle_data.json           # cached data (gitignored)
```

### Suggested Stack
- **Python** for data pull
- **Streamlit** for dashboard (fast to build, runs locally)
- **pandas** for data manipulation
- **plotly** for charts

### Dashboard Views to Build
1. **Portfolio Overview** — total revenue, cost, margin, WIP across all active projects
2. **Project Table** — sortable by margin %, revenue, hours; filterable by client/status
3. **Client Rollup** — aggregate revenue/margin per client
4. **At-Risk Projects** — projects where WIP >> InvoicedToDate or margin < threshold
5. **Staff Utilization** — hours by staff member

---

## What Still Needs to Be Figured Out
1. **Invoice endpoint** — the correct path to pull invoice history (needed for billing trend charts)
2. **Time entries** — `/time/reportbyfilter` field names need to be correct (field is probably `StartDt`/`EndDt` not `mindate`/`maxdate`)
3. **Performance** — looping 174 projects × 1 API call each = ~6 min fresh pull. Consider caching to JSON and refreshing on demand.

---

## Files in This Repo
- `bt_test*.py` — authentication debugging scripts (can be deleted)
- `bt_explore.py` — endpoint exploration script
- `gle_profitability.py` — first-pass data pull script (starting point, needs refactor)

---

## GLE Context
- ~50 active clients, 174 active projects
- 11 staff members, cost rates populated in BigTime
- Billing types: flat rate, T&M
- Owner: Colin Casey (ccasey@gllps.com)

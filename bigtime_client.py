"""
BigTime API client with rate limiting and retry logic.

Usage:
    from bigtime_client import BigTimeClient
    client = BigTimeClient()          # loads credentials from .env
    projects = client.get_projects()
"""

from pathlib import Path
import time
import requests
from dotenv import dotenv_values

# Load .env as a dict directly (avoids BOM / os.environ issues on Windows)
_ENV_PATH = Path(__file__).resolve().parent / ".env"
_cfg = dotenv_values(_ENV_PATH, encoding="utf-8-sig")


def _req(key):
    val = _cfg.get(key)
    if not val:
        raise RuntimeError(
            f"{key} not found in {_ENV_PATH}. "
            f"Keys present: {list(_cfg.keys())}"
        )
    return val


class BigTimeClient:
    """Thin wrapper around the BigTime REST API v2."""

    RATE_LIMIT_BATCH = 25       # pause after this many calls
    RATE_LIMIT_PAUSE = 3        # seconds to pause

    def __init__(self):
        self.base_url = _req("BIGTIME_BASE_URL")
        self.headers = {
            "Accept":          "application/json",
            "Content-Type":    "application/json",
            "X-auth-ApiToken": _req("BIGTIME_API_TOKEN"),
            "X-auth-realm":    _req("BIGTIME_FIRM_ID"),
        }
        self._call_count = 0

    # ── low-level helpers ────────────────────────────────────────────────

    def _throttle(self):
        """Pause every RATE_LIMIT_BATCH calls to stay under 30/min."""
        self._call_count += 1
        if self._call_count % self.RATE_LIMIT_BATCH == 0:
            time.sleep(self.RATE_LIMIT_PAUSE)

    def get(self, path, params=None):
        """GET request with throttle. Returns parsed JSON or None."""
        self._throttle()
        r = requests.get(
            f"{self.base_url}{path}",
            headers=self.headers,
            params=params,
            timeout=30,
        )
        if r.ok:
            return r.json()
        print(f"  ERROR {r.status_code} GET {path}: {r.text[:200]}")
        return None

    def post(self, path, body=None):
        """POST request with throttle. Returns parsed JSON or None."""
        self._throttle()
        r = requests.post(
            f"{self.base_url}{path}",
            headers=self.headers,
            json=body or {},
            timeout=30,
        )
        if r.ok:
            return r.json()
        print(f"  ERROR {r.status_code} POST {path}: {r.text[:200]}")
        return None

    # ── domain endpoints ─────────────────────────────────────────────────

    def get_projects(self, active_only=True):
        """Return list of projects. Set active_only=False to include inactive."""
        return self.get("/project", {"ShowInactive": str(not active_only).lower()}) or []

    def get_project_detail(self, project_id):
        return self.get(f"/project/detail/{project_id}")

    def get_task_budget(self, project_id):
        """Core profitability data — task-level budget status for a project."""
        return self.get(f"/task/BudgetStatusByProject/{project_id}") or []

    def get_clients(self):
        return self.get("/client") or []

    def get_staff(self):
        return self.get("/staff") or []

    def get_expenses(self, start_date, end_date):
        """Pull expenses for a date range (YYYY-MM-DD strings)."""
        return self.post("/expense/reportbyfilter", {
            "mindate": start_date,
            "maxdate": end_date,
            "view": "basic",
        }) or []

    def get_invoice_history(self, start_date, end_date):
        """Pull invoice history for a date range (YYYY-MM-DD strings)."""
        return self.get("/invoice/history", {
            "startDt": start_date,
            "endDt": end_date,
        }) or []

    def get_project_types(self):
        """Pull project type picklist (TypeId → name mapping)."""
        return self.get("/picklist/FieldValues/LookupProjectType") or []

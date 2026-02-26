"""
BigTime Auth Debug - tries several authentication approaches
Run: python bigtime_auth_debug.py
"""

import requests
import json

API_TOKEN = "Ctdcf3W+AFWeZU9VkamsnIjGNvMfI1gHzPCK9vUHNpXcAW883SdUT/Urvp+gI6lW"
FIRM_ID   = "akpf-qzjv-sgzv"
BASE_URL  = "https://iq.bigtime.net/BigtimeData/api/v2"

def test(label, method, url, headers, body=None):
    print(f"\n{'='*60}")
    print(f"TEST: {label}")
    print(f"URL:  {url}")
    print(f"Headers: {json.dumps({k:v[:30]+'...' if len(str(v))>30 else v for k,v in headers.items()}, indent=2)}")
    try:
        if method == "POST":
            r = requests.post(url, headers=headers, json=body or {}, timeout=15)
        else:
            r = requests.get(url, headers=headers, timeout=15)
        print(f"Status: {r.status_code}")
        print(f"Response: {r.text[:500]}")
        return r
    except Exception as e:
        print(f"Exception: {e}")
        return None

# ── Attempt 1: Firm session with token in body ───────────────────────────────
test(
    "Firm session - token in body",
    "POST",
    f"{BASE_URL}/session/firm",
    {"Content-Type": "application/json", "Accept": "application/json"},
    {"token": API_TOKEN, "firmid": FIRM_ID}
)

# ── Attempt 2: Firm session - token in header only ───────────────────────────
test(
    "Firm session - token in header X-auth-ApiToken",
    "POST",
    f"{BASE_URL}/session/firm",
    {
        "Content-Type": "application/json",
        "Accept": "application/json",
        "X-auth-ApiToken": API_TOKEN,
        "X-auth-realm": FIRM_ID,
    },
    {}
)

# ── Attempt 3: Skip session - use token directly on a data endpoint ──────────
test(
    "Direct project list - token as X-auth-ApiToken",
    "GET",
    f"{BASE_URL}/project",
    {
        "Content-Type": "application/json",
        "Accept": "application/json",
        "X-auth-ApiToken": API_TOKEN,
        "X-auth-realm": FIRM_ID,
    }
)

# ── Attempt 4: Token as X-Auth-Token (not ApiToken) ─────────────────────────
test(
    "Direct project list - token as X-Auth-Token",
    "GET",
    f"{BASE_URL}/project",
    {
        "Content-Type": "application/json",
        "Accept": "application/json",
        "X-Auth-Token": API_TOKEN,
        "X-Auth-Realm": FIRM_ID,
    }
)

# ── Attempt 5: Session with token/firmid in body (alternate casing) ──────────
test(
    "Firm session - alternate field names in body",
    "POST",
    f"{BASE_URL}/session/firm",
    {"Content-Type": "application/json", "Accept": "application/json"},
    {"Token": API_TOKEN, "FirmId": FIRM_ID}
)

# ── Attempt 6: Try the regular /session endpoint with token as password ───────
test(
    "Regular session - token as password",
    "POST",
    f"{BASE_URL}/session",
    {"Content-Type": "application/json", "Accept": "application/json"},
    {"userId": "colin@glesinc.com", "pwd": API_TOKEN}
)

print("\n" + "="*60)
print("Done. Paste ALL output above back to Claude.")
print("="*60)

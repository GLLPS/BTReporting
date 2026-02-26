import requests

API_TOKEN = "Ctdcf3W+AFWeZU9VkamsnnU5t9kEb+aKCl9E/B6KHAtZY7rhxn13fYEzVy6Iz9XV"
FIRM_ID_SLUG = "csuk-lqt-xwnw"
TENANT_ID = "17982"

print("Token length:", len(API_TOKEN))

print("\n=== TEST 1: X-auth-ApiToken + slug ===")
r = requests.get(
    "https://iq.bigtime.net/BigtimeData/api/v2/project",
    headers={"Accept": "application/json", "X-auth-ApiToken": API_TOKEN, "X-auth-realm": FIRM_ID_SLUG},
    timeout=15
)
print("Status:", r.status_code, "| Response:", r.text[:300])

print("\n=== TEST 2: X-auth-ApiToken + tenant ID ===")
r = requests.get(
    "https://iq.bigtime.net/BigtimeData/api/v2/project",
    headers={"Accept": "application/json", "X-auth-ApiToken": API_TOKEN, "X-auth-realm": TENANT_ID},
    timeout=15
)
print("Status:", r.status_code, "| Response:", r.text[:300])

print("\n=== TEST 3: POST /session/firm with tenant ID in body ===")
r = requests.post(
    "https://iq.bigtime.net/BigtimeData/api/v2/session/firm",
    json={"token": API_TOKEN, "firmid": TENANT_ID},
    headers={"Accept": "application/json", "Content-Type": "application/json"},
    timeout=15
)
print("Status:", r.status_code, "| Response:", r.text[:300])

print("\n=== TEST 4: POST /session/firm with slug in body ===")
r = requests.post(
    "https://iq.bigtime.net/BigtimeData/api/v2/session/firm",
    json={"token": API_TOKEN, "firmid": FIRM_ID_SLUG},
    headers={"Accept": "application/json", "Content-Type": "application/json"},
    timeout=15
)
print("Status:", r.status_code, "| Response:", r.text[:300])

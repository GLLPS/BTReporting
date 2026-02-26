import requests
import json

USERNAME = "ccasey@gllps.com"
PASSWORD = "Function@22"
FIRM_ID  = "csuk-lqt-xwnw"
BASE_URL = "https://iq.bigtime.net/BigtimeData/api/v2"

print("=== STEP 1: Authenticate ===")
r = requests.post(
    f"{BASE_URL}/session",
    json={"UserName": USERNAME, "Pwd": PASSWORD},
    headers={"Content-Type": "application/json", "Accept": "application/json"},
    timeout=15
)
print("Status:", r.status_code)
print("Response:", r.text[:1000])

if r.status_code == 200:
    data = r.json()
    print("\nFull response:", json.dumps(data, indent=2))
    
    # Try to find the token in the response
    session_token = (data.get("token") or data.get("Token") or 
                     data.get("access_token") or data.get("AccessToken"))
    print("\nSession token:", session_token)

    print("\n=== STEP 2: Select firm ===")
    r2 = requests.post(
        f"{BASE_URL}/session/firm",
        json={"token": session_token, "firmid": FIRM_ID},
        headers={"Content-Type": "application/json", "Accept": "application/json"},
        timeout=15
    )
    print("Status:", r2.status_code)
    print("Response:", r2.text[:2000])

    if r2.status_code == 200:
        data2 = r2.json()
        firm_token = data2.get("token") or data2.get("Token")
        print("\nFirm token:", firm_token)

        print("\n=== STEP 3: Get projects (JSON) ===")
        r3 = requests.get(
            f"{BASE_URL}/project",
            headers={
                "Accept": "application/json",
                "X-auth-token": firm_token,
                "X-auth-realm": FIRM_ID
            },
            timeout=15
        )
        print("Status:", r3.status_code)
        print("Response:", r3.text[:500])

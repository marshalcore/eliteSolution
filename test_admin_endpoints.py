import requests
import json
import os

BASE_URL = "http://localhost:8000/api/v1/admin"

def get_admin_token():
    # Try to read token from file
    if os.path.exists("admin_token.txt"):
        with open("admin_token.txt", "r") as f:
            return f.read().strip()
    return "YOUR_ADMIN_TOKEN_HERE"  # Fallback

ADMIN_TOKEN = get_admin_token()

endpoints_to_test = [
    ("GET", "/users", None),
    ("GET", "/transactions", None),
    ("GET", "/transactions?status=pending", None),
]

def test_endpoints():
    headers = {
        "Authorization": f"Bearer {ADMIN_TOKEN}",
        "Content-Type": "application/json"
    }
    
    for method, endpoint, data in endpoints_to_test:
        url = BASE_URL + endpoint
        try:
            if method == "GET":
                response = requests.get(url, headers=headers)
            elif method == "POST":
                response = requests.post(url, json=data, headers=headers)
            
            status_color = "✅" if response.status_code == 200 else "❌"
            print(f"{status_color} {method} {endpoint}: {response.status_code}")
            
            if response.status_code != 200:
                print(f"   Response: {response.text}")
                
        except Exception as e:
            print(f"❌ Error testing {method} {endpoint}: {e}")

if __name__ == "__main__":
    test_endpoints()
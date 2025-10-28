import requests
import json
import os

BASE_URL = "http://localhost:8000/api/v1/admin"

def get_admin_token():
    if os.path.exists("admin_token.txt"):
        with open("admin_token.txt", "r") as f:
            return f.read().strip()
    return None

def test_all_admin_features():
    token = get_admin_token()
    if not token:
        print("❌ No admin token found. Run test_admin_auth.py first.")
        return
    
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    
    # Test all major admin endpoints
    endpoints = [
        ("GET", "/users", "Get all users"),
        ("GET", "/transactions", "Get all transactions"),
        ("GET", "/transactions?status=pending", "Get pending transactions"),
        ("GET", "/kyc/pending", "Get pending KYC applications"),
    ]
    
    print("🔧 Testing Admin Endpoints...")
    print("=" * 50)
    
    success_count = 0
    total_count = len(endpoints)
    
    for method, endpoint, description in endpoints:
        try:
            url = BASE_URL + endpoint
            if method == "GET":
                response = requests.get(url, headers=headers)
            elif method == "POST":
                response = requests.post(url, headers=headers)
            
            if response.status_code == 200:
                print(f"✅ {description}: SUCCESS")
                data = response.json()
                if isinstance(data, list):
                    print(f"   📊 Count: {len(data)}")
                success_count += 1
            else:
                print(f"❌ {description}: FAILED ({response.status_code})")
                print(f"   Response: {response.text}")
                
        except Exception as e:
            print(f"❌ {description}: ERROR - {e}")
    
    print("=" * 50)
    print(f"📈 Results: {success_count}/{total_count} tests passed")
    
    if success_count == total_count:
        print("🎉 All admin endpoints are working perfectly!")
    else:
        print("⚠️ Some endpoints need attention.")

if __name__ == "__main__":
    test_all_admin_features()
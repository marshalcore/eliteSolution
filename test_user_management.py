import requests
import json
import os

BASE_URL = "http://localhost:8000/api/v1/admin"

def get_admin_token():
    if os.path.exists("admin_token.txt"):
        with open("admin_token.txt", "r") as f:
            return f.read().strip()
    return None

def test_user_management():
    token = get_admin_token()
    if not token:
        print("❌ No admin token found.")
        return
    
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    
    # First, get users to see what we have
    try:
        response = requests.get(f"{BASE_URL}/users", headers=headers)
        if response.status_code == 200:
            users = response.json()
            print(f"✅ Found {len(users)} users in system")
            
            if users:
                # Show first few users
                print("\n📋 Sample Users:")
                for i, user in enumerate(users[:3]):  # Show first 3 users
                    print(f"  {i+1}. {user.get('email', 'N/A')} - KYC: {user.get('kyc_status', 'N/A')}")
        
    except Exception as e:
        print(f"❌ Error getting users: {e}")

if __name__ == "__main__":
    test_user_management()
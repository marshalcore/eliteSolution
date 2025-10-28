import requests
import json
import os

BASE_URL = "http://localhost:8000/api/v1/admin"

def get_admin_token():
    if os.path.exists("admin_token.txt"):
        with open("admin_token.txt", "r") as f:
            return f.read().strip()
    return None

def test_kyc_flow():
    token = get_admin_token()
    if not token:
        print("❌ No admin token found. Run test_admin_auth.py first.")
        return
    
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    
    try:
        # Get pending KYC applications - CORRECTED ENDPOINT
        response = requests.get(f"{BASE_URL}/kyc/pending", headers=headers)
        print(f"Pending KYC Response: {response.status_code}")
        
        if response.status_code == 200:
            applications = response.json()
            print(f"✅ Found {len(applications)} pending KYC applications")
            
            if applications:
                # Show KYC application details
                first_app = applications[0]
                print(f"\n📋 KYC Application Details:")
                print(f"   User ID: {first_app.get('id')}")
                print(f"   Email: {first_app.get('email')}")
                print(f"   Name: {first_app.get('first_name')} {first_app.get('last_name')}")
                print(f"   KYC Status: {first_app.get('kyc_status')}")
                
                # Test approving the KYC application
                review_data = {
                    "user_id": first_app["id"],
                    "status": "verified"  # or "rejected"
                }
                
                print(f"\n🔄 Approving KYC application...")
                response = requests.post(f"{BASE_URL}/kyc/review", json=review_data, headers=headers)
                print(f"KYC Review Response: {response.status_code} - {response.text}")
                
        else:
            print(f"❌ Failed to get pending KYC: {response.text}")
            
    except Exception as e:
        print(f"❌ KYC test failed: {e}")

if __name__ == "__main__":
    test_kyc_flow()
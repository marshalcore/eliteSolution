import requests
import json

BASE_URL = "http://localhost:8000/api/v1/admin"

def debug_admin_login():
    # Test with simple data first
    test_data = [
        {
            "email": "mail.gacode@gmail.com",
            "password": "test123"
        },
        {
            "email": "mail.g9teluxuries.org@gmail.com", 
            "password": "test123"
        }
    ]
    
    for login_data in test_data:
        print(f"\n🔍 Testing login for: {login_data['email']}")
        try:
            response = requests.post(f"{BASE_URL}/login", json=login_data, timeout=10)
            print(f"Status: {response.status_code}")
            print(f"Response: {response.text}")
            
            if response.status_code == 500:
                print("❌ Server error - check server logs")
            elif response.status_code == 401:
                print("❌ Invalid credentials")
            elif response.status_code == 200:
                print("✅ Login successful - OTP sent")
                
        except requests.exceptions.RequestException as e:
            print(f"❌ Request failed: {e}")

if __name__ == "__main__":
    debug_admin_login()
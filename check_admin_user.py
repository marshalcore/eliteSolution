import requests
import json

BASE_URL = "http://localhost:8000/api/v1/admin"

def test_admin_auth_flow():
    # Use one of your actual admin emails
    login_data = {
        "email": "mail.gacode@gmail.com",  # Use your actual admin email
        "password": "mail.gacode@"  # You need to know the password for this admin
    }
    
    try:
        print(f"Attempting login for: {login_data['email']}")
        response = requests.post(f"{BASE_URL}/login", json=login_data)
        print(f"Login Response: {response.status_code} - {response.text}")
        
        if response.status_code == 200:
            # Step 2: Verify OTP - FIXED with correct structure
            verify_data = {
                "email": login_data["email"],
                "code": "123456",  # You'll need to check your email for the actual OTP
                "purpose": "admin_login"  # ✅ This field is required
            }
            
            print(f"Waiting for OTP verification...")
            response = requests.post(f"{BASE_URL}/verify-login", json=verify_data)
            print(f"OTP Verify Response: {response.status_code} - {response.text}")
            
            if response.status_code == 200:
                token = response.json().get("access_token")
                print(f"✅ Admin token: {token}")
                
                # Save token to file for other tests
                with open("admin_token.txt", "w") as f:
                    f.write(token)
                print("✅ Token saved to admin_token.txt")
                return token
        else:
            print("❌ Login failed. Check your email and password.")
        return None
        
    except Exception as e:
        print(f"❌ Auth test failed: {e}")
        return None

if __name__ == "__main__":
    test_admin_auth_flow()
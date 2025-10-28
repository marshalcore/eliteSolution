import requests
import json

BASE_URL = "http://localhost:8000/api/v1/admin"

def test_admin_auth_flow():
    # Use the reset credentials
    login_data = {
        "email": "mail.gacode@gmail.com",
        "password": "Admin123!"  # Use the new password from reset
    }
    
    try:
        print(f"🔐 Attempting login for: {login_data['email']}")
        response = requests.post(f"{BASE_URL}/login", json=login_data)
        print(f"Login Response: {response.status_code} - {response.text}")
        
        if response.status_code == 200:
            print("✅ Login successful! OTP should be sent to email.")
            print("📧 Please check your email for the OTP code.")
            
            # Ask user to input the actual OTP they receive
            otp_code = input("Enter the OTP code from your email: ").strip()
            
            # Verify OTP with correct structure
            verify_data = {
                "email": login_data["email"],
                "code": otp_code,  # Use the actual OTP from email
                "purpose": "admin_login"  # ✅ Required field
            }
            
            print("🔄 Verifying OTP...")
            response = requests.post(f"{BASE_URL}/verify-login", json=verify_data)
            print(f"OTP Verify Response: {response.status_code} - {response.text}")
            
            if response.status_code == 200:
                token = response.json().get("access_token")
                print(f"✅ Admin token obtained successfully!")
                print(f"🔑 Token: {token}")
                
                # Save token to file for other tests
                with open("admin_token.txt", "w") as f:
                    f.write(token)
                print("💾 Token saved to admin_token.txt")
                return token
            else:
                print("❌ OTP verification failed")
        else:
            print("❌ Login failed")
        return None
        
    except Exception as e:
        print(f"❌ Auth test failed: {e}")
        return None

if __name__ == "__main__":
    test_admin_auth_flow()
import requests
import time

def test_endpoints():
    base_url = "http://localhost:8000"
    endpoints = ["/", "/health", "/api/v1/auth/"]
    
    for endpoint in endpoints:
        try:
            response = requests.get(f"{base_url}{endpoint}", timeout=5)
            print(f"✅ {endpoint}: {response.status_code}")
            if response.status_code == 200:
                print(f"   Response: {response.json()}")
        except Exception as e:
            print(f"❌ {endpoint}: {e}")
    
    print("\n📊 Container status:")
    import subprocess
    result = subprocess.run(["docker", "ps"], capture_output=True, text=True)
    print(result.stdout)

if __name__ == "__main__":
    test_endpoints()

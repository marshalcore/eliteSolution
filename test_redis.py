import requests
import json

def test_redis_features():
    base_url = "http://localhost:8000"
    
    # Test if Redis is working by checking the health endpoint
    health = requests.get(f"{base_url}/health").json()
    print(f"Health status: {health}")
    
    # Test a simple cache operation (you might need to adapt this based on your actual API)
    print("Redis integration test complete!")
    
if __name__ == "__main__":
    test_redis_features()

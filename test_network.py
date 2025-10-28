import socket
import os
from urllib.parse import urlparse
from app.core.config import settings

def test_network():
    try:
        # Extract hostname from DATABASE_URL
        parsed = urlparse(settings.DATABASE_URL)
        hostname = parsed.hostname
        port = parsed.port or 5432
        
        print(f"🔧 Testing network connectivity to: {hostname}:{port}")
        
        # Test socket connection
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(10)
        result = sock.connect_ex((hostname, port))
        sock.close()
        
        if result == 0:
            print("✅ Network connectivity: SUCCESS")
        else:
            print(f"❌ Network connectivity: FAILED (error code: {result})")
            print("💡 Check your internet connection and firewall settings")
            
    except Exception as e:
        print(f"❌ Network test failed: {e}")

if __name__ == "__main__":
    test_network()
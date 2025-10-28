import os
from app.core.config import settings

def check_config():
    print("🔧 Checking database configuration...")
    print(f"Database URL: {settings.DATABASE_URL}")
    
    # Check if it's a Neon URL
    if "neon.tech" in settings.DATABASE_URL:
        print("✅ Detected Neon.tech database")
        
        # Check for required components
        if "pooler" in settings.DATABASE_URL:
            print("✅ Using connection pooler")
        else:
            print("⚠️  Not using connection pooler - consider adding '-pooler' to hostname")
            
        if "sslmode=require" in settings.DATABASE_URL:
            print("✅ SSL mode is required")
        else:
            print("❌ SSL mode not set - Neon requires SSL")
            
    else:
        print("❌ Not a Neon database URL")

if __name__ == "__main__":
    check_config()
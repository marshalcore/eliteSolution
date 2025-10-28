import os
import sys
sys.path.append('.')
from app.db.session import SessionLocal

def test_neon_connection():
    try:
        db = SessionLocal()
        result = db.execute("SELECT version()").fetchone()
        print("✅ Neon PostgreSQL connection successful!")
        print(f"✅ Database: {result[0]}")
        db.close()
        return True
    except Exception as e:
        print(f"❌ Connection failed: {e}")
        return False

if __name__ == "__main__":
    test_neon_connection()
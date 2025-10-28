import asyncio
import sys
import os

# Add your project root to Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.db import get_db
from app.models.user import User
from sqlalchemy import select

async def test_db():
    try:
        # Get database session
        db_gen = get_db()
        db = next(db_gen)
        
        # Test query
        result = db.query(User).limit(1).all()
        print("✅ Database connection successful!")
        print(f"✅ Found {len(result)} users in database")
        return True
    except Exception as e:
        print(f"❌ Database connection failed: {e}")
        return False
    finally:
        try:
            next(db_gen)  # Close the generator
        except StopIteration:
            pass

if __name__ == "__main__":
    asyncio.run(test_db())
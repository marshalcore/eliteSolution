import os

# Set Neon database URL (replace with your actual credentials)
neon_url = "postgresql://your_username:your_password@ep-green-credit-a19hsnai-pooler.ap-southeast-1.aws.neon.tech/neondb?sslmode=require"

# Update environment variable
os.environ['DATABASE_URL'] = neon_url

print("✅ Switched to PostgreSQL Neon database")
print(f"Database URL: {os.environ['DATABASE_URL']}")

# Test the connection
try:
    from app.db.session import SessionLocal
    db = SessionLocal()
    result = db.execute("SELECT version()").fetchone()
    print(f"✅ Connection successful! Database: {result[0]}")
    db.close()
except Exception as e:
    print(f"❌ Connection failed: {e}")
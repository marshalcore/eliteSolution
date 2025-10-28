import os
import sys

# Set SQLite for development
os.environ['DATABASE_URL'] = 'sqlite:///./elitesolution.db'

print("✅ Using SQLite database for development")
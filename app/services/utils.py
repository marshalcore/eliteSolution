# backend/app/services/utils.py
import random
from sqlalchemy import text
from app.db import SessionLocal

def generate_account_number(length: int = 10) -> str:
    """
    Generate a random account number of given length.
    Ensures uniqueness by checking against the accounts table.
    """
    db = SessionLocal()
    try:
        while True:
            num = ''.join(str(random.randint(0, 9)) for _ in range(length))
            r = db.execute(
                text("SELECT 1 FROM accounts WHERE account_number = :n"),
                {"n": num}
            ).first()
            if not r:  # If no match found, it's unique
                return num
    finally:
        db.close()

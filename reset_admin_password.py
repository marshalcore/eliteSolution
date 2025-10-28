import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.db import SessionLocal
from app.models.user import User
from app.core.security import get_password_hash

def reset_admin_password():
    db = SessionLocal()
    try:
        # Get the first admin user
        admin_user = db.query(User).filter(User.email == "mail.gacode@gmail.com").first()
        
        if not admin_user:
            print("❌ Admin user not found!")
            return False
        
        # Reset to a known password
        new_password = "Admin123!"  # Strong password we'll use
        admin_user.hashed_password = get_password_hash(new_password)
        
        db.commit()
        
        print("✅ Admin password reset successfully!")
        print(f"Email: {admin_user.email}")
        print(f"New Password: {new_password}")
        print("\n📝 Use these credentials in the next test.")
        return True
        
    except Exception as e:
        print(f"❌ Error resetting password: {e}")
        db.rollback()
        return False
    finally:
        db.close()

if __name__ == "__main__":
    reset_admin_password()
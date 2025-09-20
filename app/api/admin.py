from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.db import get_db
from app.models.user import User
from app.models.transaction import Transaction
from app.schemas.admin import AdminCreate, AdminLogin
from app.schemas.otp import OTPVerify
from app.core.security import (
    verify_password,
    get_password_hash,
    create_access_token,
    get_current_user_db,
)

# ----------------------------
#  AUTH HELPERS
# ----------------------------
def get_current_admin(current_user: User = Depends(get_current_user_db)):
    """Ensure the logged-in user is an admin."""
    if not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Not authorized as admin")
    return current_user


# ----------------------------
#  ROUTER SETUP
# ----------------------------
router = APIRouter(
    prefix="/api/v1/admin",
    tags=["admin"],
)


# ----------------------------
#  PUBLIC ROUTES (NO TOKEN REQUIRED)
# ----------------------------
@router.post("/register")
def admin_register(data: AdminCreate, db: Session = Depends(get_db)):
    existing = db.query(User).filter(User.email == data.email).first()
    if existing:
        raise HTTPException(status_code=400, detail="Admin already exists")

    hashed_pw = get_password_hash(data.password)
    admin = User(
        email=data.email,
        hashed_password=hashed_pw,
        first_name=data.first_name or "Admin",
        last_name=data.last_name or "Account",
        is_admin=True,
        is_verified=False,
        kyc_status="pending",
    )
    db.add(admin)
    db.commit()
    db.refresh(admin)

    from app.models.otp import OTPPurpose
    from app.services.otp_service import generate_otp, send_otp_email

    otp_code = generate_otp(admin.id, OTPPurpose.ADMIN_REGISTRATION, db)

    html_content = f"""
    <html>
      <body>
        <h2>Admin Verification</h2>
        <p>Welcome, Admin!</p>
        <p>Your OTP code is <b>{otp_code}</b></p>
      </body>
    </html>
    """
    send_otp_email(admin.email, otp_code, "admin registration", html_content=html_content)

    return {"message": "Admin registered. Please verify with OTP."}


@router.post("/verify-registration")
def verify_admin_registration(data: OTPVerify, db: Session = Depends(get_db)):
    from app.models.otp import OTPPurpose
    from app.services.otp_service import verify_otp

    user = db.query(User).filter(User.email == data.email).first()
    if not user or not user.is_admin:
        raise HTTPException(status_code=403, detail="Not authorized as admin")

    if not verify_otp(user.id, data.code, OTPPurpose.ADMIN_REGISTRATION, db):
        raise HTTPException(status_code=400, detail="Invalid or expired OTP")

    user.is_verified = True
    db.commit()
    db.refresh(user)
    return {"message": "Admin registration verified successfully"}


@router.post("/login")
def admin_login(data: AdminLogin, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == data.email).first()
    if not user or not verify_password(data.password, user.hashed_password):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")

    if not user.is_admin:
        raise HTTPException(status_code=403, detail="This account is not an admin")

    from app.models.otp import OTPPurpose
    from app.services.otp_service import generate_otp, send_otp_email

    otp_code = generate_otp(user.id, OTPPurpose.ADMIN_LOGIN, db)

    html_content = f"""
    <html>
      <body>
        <h2>Admin Login Verification</h2>
        <p>Hi {user.first_name},</p>
        <p>Your OTP code is <b>{otp_code}</b></p>
      </body>
    </html>
    """
    send_otp_email(user.email, otp_code, "admin login", html_content=html_content)

    return {"message": "Admin OTP sent to email. Verify to complete login."}


@router.post("/verify-login")
def verify_admin_login(data: OTPVerify, db: Session = Depends(get_db)):
    from app.models.otp import OTPPurpose
    from app.services.otp_service import verify_otp

    user = db.query(User).filter(User.email == data.email).first()
    if not user or not user.is_admin:
        raise HTTPException(status_code=403, detail="Not authorized as admin")

    if not verify_otp(user.id, data.code, OTPPurpose.ADMIN_LOGIN, db):
        raise HTTPException(status_code=400, detail="Invalid or expired OTP")

    token = create_access_token({"sub": user.id, "is_admin": True})
    return {"access_token": token, "token_type": "bearer"}


# ----------------------------
#  PROTECTED ROUTES (TOKEN REQUIRED)
# ----------------------------
@router.post("/logout")
def admin_logout(current_admin: User = Depends(get_current_admin)):
    return {"message": "Admin logged out successfully"}


@router.delete("/user/{user_id}")
def delete_user(
    user_id: int,
    db: Session = Depends(get_db),
    current_admin: User = Depends(get_current_admin),
):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    db.delete(user)
    db.commit()
    return {"message": f"User {user.email} deleted"}


@router.get("/users")
def get_all_users(db: Session = Depends(get_db), current_admin: User = Depends(get_current_admin)):
    return db.query(User).all()


@router.get("/transactions")
def get_transactions(
    status: str = None,
    db: Session = Depends(get_db),
    current_admin: User = Depends(get_current_admin),
):
    q = db.query(Transaction)
    if status:
        q = q.filter(Transaction.status == status)
    return q.all()


@router.post("/transactions/{txn_id}/approve")
def approve_transaction(
    txn_id: int,
    db: Session = Depends(get_db),
    current_admin: User = Depends(get_current_admin),
):
    txn = db.query(Transaction).filter(Transaction.id == txn_id).first()
    if not txn:
        raise HTTPException(status_code=404, detail="Transaction not found")
    txn.status = "approved"
    db.commit()
    return {"message": f"Transaction {txn.id} approved"}


@router.post("/transactions/{txn_id}/reject")
def reject_transaction(
    txn_id: int,
    db: Session = Depends(get_db),
    current_admin: User = Depends(get_current_admin),
):
    txn = db.query(Transaction).filter(Transaction.id == txn_id).first()
    if not txn:
        raise HTTPException(status_code=404, detail="Transaction not found")
    txn.status = "rejected"
    db.commit()
    return {"message": f"Transaction {txn.id} rejected"}


@router.put("/users/{user_id}/reset-password")
def reset_user_password(
    user_id: int,
    new_password: str,
    db: Session = Depends(get_db),
    current_admin: User = Depends(get_current_admin),
):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    user.hashed_password = get_password_hash(new_password)
    db.commit()
    return {"message": f"Password reset for user {user.email}"}


@router.put("/users/{user_id}/update")
def update_user_details(
    user_id: int,
    email: str = None,
    phone: str = None,
    db: Session = Depends(get_db),
    current_admin: User = Depends(get_current_admin),
):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    if email:
        user.email = email
    if phone:
        user.phone = phone

    db.commit()
    db.refresh(user)
    return {"message": f"User {user.id} updated", "user": {"email": user.email, "phone": user.phone}}

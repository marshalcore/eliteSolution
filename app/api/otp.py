# app/api/otp.py
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.otp import OTPVerify
from app.models.otp import OTPPurpose
from app.models.user import User
from app.services.otp_service import generate_otp, send_otp_email, verify_otp
from app.core.security import get_current_user_db

router = APIRouter(prefix="/api/v1/otp", tags=["otp"])


@router.post("/resend")
def resend_otp(
    purpose: OTPPurpose,
    current_user: User = Depends(get_current_user_db),
    db: Session = Depends(get_db),
):
    """Resend OTP for a given purpose (requires authenticated user)."""
    otp_code = generate_otp(current_user.id, purpose, db)
    send_otp_email(current_user.email, otp_code, purpose.value)

    return {
        "success": True,
        "message": f"OTP sent to {current_user.email} for {purpose.value}",
    }


@router.post("/verify")
def verify_otp_endpoint(
    otp_data: OTPVerify,
    db: Session = Depends(get_db),
):
    """Verify OTP by email + purpose + code (does not require authentication)."""
    user = db.query(User).filter(User.email == otp_data.email).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    if not verify_otp(user.id, otp_data.code, otp_data.purpose, db):
        raise HTTPException(status_code=400, detail="Invalid or expired OTP")

    return {"success": True, "message": "OTP verified successfully"}

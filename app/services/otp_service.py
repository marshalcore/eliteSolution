# app/services/otp_service.py
import random
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from app.models.otp import OTP, OTPPurpose
from app.utils.email_utils import send_email


def generate_otp(user_id: int, purpose: OTPPurpose, db: Session) -> str:
    code = f"{random.randint(100000, 999999)}"

    # Invalidate any existing OTPs for same purpose
    db.query(OTP).filter(
        OTP.user_id == user_id,
        OTP.purpose == purpose,
        OTP.is_used == False
    ).update({"is_used": True})
    
    otp = OTP(
        user_id=user_id,
        code=code,
        purpose=purpose,
        expires_at=datetime.utcnow() + timedelta(minutes=10),
        is_used=False,
    )
    db.add(otp)
    db.commit()
    db.refresh(otp)

    return code


def send_otp_email(user_email: str, code: str, purpose: str, html_content: str = None):
    subject = f"Your OTP for {purpose}"

    # If no custom HTML is provided, use default template
    if not html_content:
        html_content = f"""
        <h2>Your OTP Code</h2>
        <p>Your OTP code for <b>{purpose}</b> is:</p>
        <p style="font-size:24px; font-weight:bold; color:#004080;">{code}</p>
        <p>This code will expire in 10 minutes.</p>
        <p>If you didn't request this, please ignore this email.</p>
        """

    send_email(user_email, subject, html_content)


def verify_otp(user_id: int, otp_code: str, purpose: OTPPurpose, db: Session) -> bool:
    otp = db.query(OTP).filter(
        OTP.user_id == user_id,
        OTP.code == otp_code,
        OTP.purpose == purpose,
        OTP.is_used == False,
        OTP.expires_at > datetime.utcnow()
    ).first()

    if not otp:
        return False

    otp.is_used = True
    db.commit()
    return True

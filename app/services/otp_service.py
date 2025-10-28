# app/services/otp_service.py - FIXED VERSION
import random
import string
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from fastapi import HTTPException

from app.models.otp import OTP, OTPPurpose
from app.core.config import settings
from app.services.email_service import send_email
import logging

logger = logging.getLogger(__name__)

def generate_otp_code(length: int = 6) -> str:
    """Generate a random OTP code"""
    return ''.join(random.choices(string.digits, k=length))

def generate_otp(user_id: int, purpose: OTPPurpose, db: Session, length: int = 6) -> str:
    """Generate and save OTP to database"""
    
    # Invalidate any existing OTPs for same user and purpose
    db.query(OTP).filter(
        OTP.user_id == user_id,
        OTP.purpose == purpose,
        OTP.is_used == False
    ).update({"is_used": True})
    
    # Generate new OTP
    code = generate_otp_code(length)
    expires_at = datetime.now() + timedelta(minutes=settings.OTP_EXPIRY_MINUTES)
    
    otp = OTP(
        user_id=user_id,
        code=code,
        purpose=purpose,
        expires_at=expires_at
    )
    
    db.add(otp)
    db.commit()
    db.refresh(otp)
    
    return code

def verify_otp(user_id: int, code: str, purpose: OTPPurpose, db: Session) -> bool:
    """Verify OTP code"""
    otp = db.query(OTP).filter(
        OTP.user_id == user_id,
        OTP.code == code,
        OTP.purpose == purpose,
        OTP.is_used == False,
        OTP.expires_at > datetime.now()
    ).first()
    
    if otp:
        # Mark OTP as used
        otp.is_used = True
        otp.used_at = datetime.now()
        db.commit()
        return True
    
    return False

def can_resend_otp(user_id: int, purpose: OTPPurpose, db: Session) -> tuple[bool, int]:
    """Check if OTP can be resent and return remaining cooldown seconds"""
    # Find the most recent OTP for this user and purpose
    recent_otp = db.query(OTP).filter(
        OTP.user_id == user_id,
        OTP.purpose == purpose
    ).order_by(OTP.created_at.desc()).first()
    
    if not recent_otp:
        return True, 0
    
    # Check cooldown period (30 seconds)
    cooldown_period = timedelta(seconds=30)
    time_since_last = datetime.now() - recent_otp.created_at
    
    if time_since_last < cooldown_period:
        remaining_seconds = int((cooldown_period - time_since_last).total_seconds())
        return False, remaining_seconds
    
    return True, 0

def resend_otp(user_id: int, purpose: OTPPurpose, db: Session, user_email: str = None) -> dict:
    """Resend OTP with rate limiting and cooldown - FIXED VERSION"""
    
    # ✅ FIX: Get user email without triggering relationship mapping
    if not user_email:
        # Use raw SQL to avoid relationship issues
        from sqlalchemy import text
        result = db.execute(
            text("SELECT email FROM users WHERE id = :user_id"), 
            {"user_id": user_id}
        ).first()
        
        if not result:
            raise HTTPException(status_code=404, detail="User not found")
        
        user_email = result[0]  # Get email from first column
    
    # Check resend cooldown
    can_resend, remaining_seconds = can_resend_otp(user_id, purpose, db)
    if not can_resend:
        raise HTTPException(
            status_code=429,
            detail=f"Please wait {remaining_seconds} seconds before requesting a new OTP"
        )
    
    # Generate new OTP
    new_otp_code = generate_otp(user_id, purpose, db)
    
    # Send OTP via email with fallback
    try:
        email_sent = send_otp_email(user_email, new_otp_code, purpose.value)
        
        if not email_sent:
            # If email fails, log to console for development
            logger.warning(f"📧 Email failed, OTP for {user_email}: {new_otp_code}")
        
        return {
            "message": "OTP sent successfully",
            "cooldown_remaining": 30,
            "purpose": purpose.value
        }
    except Exception as e:
        # Rollback OTP creation if email fails
        db.rollback()
        raise HTTPException(
            status_code=500, 
            detail="Failed to send OTP. Please try again."
        )

def send_otp_email(email: str, otp_code: str, purpose: str, html_content: str = None) -> bool:
    """Send OTP email with professional template and fallback to console"""
    
    purpose_display = {
        "registration": "Email Verification",
        "login": "Login Verification", 
        "password_reset": "Password Reset",
        "pin_reset": "PIN Reset",  # ✅ ADDED: For PIN reset emails
        "admin_registration": "Admin Registration",
        "admin_login": "Admin Login",
        "change_email": "Email Change Verification",
        "change_phone": "Phone Change Verification"
    }.get(purpose, "Verification")
    
    if not html_content:
        html_content = f"""
        <html>
          <body style="font-family: Arial, sans-serif; margin:0; padding:0;">
            <table width="100%" bgcolor="#f9f9f9" cellpadding="0" cellspacing="0" style="padding:20px 0;">
              <tr>
                <td align="center">
                  <table width="600" cellpadding="0" cellspacing="0" bgcolor="#ffffff" style="border-radius:8px; overflow:hidden;">
                    <tr bgcolor="#004080">
                      <td style="padding:20px; text-align:center;">
                        <h1 style="color:white; margin:0;">EliteSolution</h1>
                      </td>
                    </tr>
                    <tr>
                      <td style="padding:30px; text-align:center;">
                        <h2 style="color:#333;">{purpose_display}</h2>
                        <p style="color:#555;">Use the OTP below to complete your {purpose_display.lower()}:</p>
                        <p style="font-size:32px; font-weight:bold; color:#004080; letter-spacing:5px;">{otp_code}</p>
                        <p style="color:#777;">This code will expire in 10 minutes.</p>
                        <p style="color:#999; font-size:12px;">If you didn't request this, please ignore this email.</p>
                      </td>
                    </tr>
                    <tr bgcolor="#f1f1f1">
                      <td style="padding:15px; text-align:center; font-size:12px; color:#777;">
                        EliteSolution © 2025
                      </td>
                    </tr>
                  </table>
                </td>
              </tr>
            </table>
          </body>
        </html>
        """
    
    subject = f"{purpose_display} Code - EliteSolution"
    
    # ✅ Try to send email with multi-port fallback
    email_sent = send_email(
        to_email=email,
        subject=subject,
        html_body=html_content,
        html_content=html_content
    )
    
    # ✅ FALLBACK: If email fails, print to console for development
    if not email_sent:
        print(f"🎯 OTP for {email}: {otp_code} (Purpose: {purpose})")
        print(f"📧 Email sending failed, but OTP is: {otp_code}")
        logger.info(f"OTP for {email}: {otp_code} (Email service unavailable)")
    
    return email_sent

def get_otp_stats(user_id: int, db: Session) -> dict:
    """Get OTP statistics for a user"""
    today = datetime.now().date()
    
    # Count OTPs sent today
    otps_today = db.query(OTP).filter(
        OTP.user_id == user_id,
        OTP.created_at >= today
    ).count()
    
    # Get last OTP sent time
    last_otp = db.query(OTP).filter(
        OTP.user_id == user_id
    ).order_by(OTP.created_at.desc()).first()
    
    return {
        "otps_sent_today": otps_today,
        "last_otp_sent": last_otp.created_at.isoformat() if last_otp else None,
        "daily_limit": getattr(settings, 'MAX_OTP_DAILY', 10)
    }

def cleanup_expired_otps(db: Session):
    """Clean up expired OTPs from database"""
    expired_count = db.query(OTP).filter(
        OTP.expires_at < datetime.now()
    ).delete()
    
    db.commit()
    return expired_count
# app/api/account_management.py
from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from sqlalchemy.orm import Session
from pydantic import BaseModel, EmailStr
from typing import Optional
import re

from app.db import get_db
from app.models.user import User
from app.models.otp import OTPPurpose
from app.core.security import get_current_user, get_password_hash, verify_password
from app.services.otp_service import generate_otp, verify_otp, send_otp_email, resend_otp
from app.services.email_validator import validate_email_address

router = APIRouter(prefix="/api/v1/account", tags=["account-management"])

# ----------------------------
# REQUEST/RESPONSE MODELS
# ----------------------------

class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str
    confirm_password: str

class ChangeEmailRequest(BaseModel):
    new_email: EmailStr
    password: str  # Confirm password for security

class ChangePhoneRequest(BaseModel):
    new_phone: str
    password: str  # Confirm password for security

class VerifyChangeRequest(BaseModel):
    code: str
    purpose: str  # change_email or change_phone

class ResendOTPRequest(BaseModel):
    purpose: str

class AccountStatusResponse(BaseModel):
    email_verified: bool
    phone_verified: bool
    kyc_status: str
    two_factor_enabled: bool
    language_preference: str
    last_password_change: Optional[str]

class SecuritySettingsResponse(BaseModel):
    two_factor_enabled: bool
    login_alerts: bool
    security_questions_set: bool

# ----------------------------
# UTILITY FUNCTIONS
# ----------------------------

def validate_phone_number(phone: str) -> bool:
    """Validate international phone number format"""
    # Basic international phone validation
    pattern = r'^\+?[1-9]\d{1,14}$'
    return bool(re.match(pattern, phone))

def validate_password_strength(password: str) -> bool:
    """Validate password strength"""
    if len(password) < 8:
        return False
    if not any(c.isupper() for c in password):
        return False
    if not any(c.islower() for c in password):
        return False
    if not any(c.isdigit() for c in password):
        return False
    return True

# ----------------------------
# ACCOUNT MANAGEMENT ENDPOINTS
# ----------------------------

@router.get("/status", response_model=AccountStatusResponse)
def get_account_status(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get comprehensive account status"""
    return {
        "email_verified": current_user.email_verified,
        "phone_verified": current_user.phone_verified,
        "kyc_status": current_user.kyc_status,
        "two_factor_enabled": current_user.two_factor_enabled,
        "language_preference": current_user.language_preference,
        "last_password_change": current_user.last_password_change.isoformat() if current_user.last_password_change else None
    }

@router.post("/change-password")
def change_password(
    request: ChangePasswordRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Change user password with security validation"""
    
    # Verify current password
    if not verify_password(request.current_password, current_user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Current password is incorrect"
        )
    
    # Check if new password matches confirmation
    if request.new_password != request.confirm_password:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="New password and confirmation do not match"
        )
    
    # Validate password strength
    if not validate_password_strength(request.new_password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Password must be at least 8 characters with uppercase, lowercase, and numbers"
        )
    
    # Check if new password is different from current
    if verify_password(request.new_password, current_user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="New password must be different from current password"
        )
    
    # Update password
    current_user.hashed_password = get_password_hash(request.new_password)
    current_user.last_password_change = db.func.now()
    db.commit()
    
    # Send security notification email
    try:
        html_content = f"""
        <html>
          <body style="font-family: Arial, sans-serif;">
            <h2>Password Changed Successfully</h2>
            <p>Your password was changed on {db.func.now().strftime('%Y-%m-%d %H:%M:%S')}.</p>
            <p>If you didn't make this change, please contact support immediately.</p>
          </body>
        </html>
        """
        send_otp_email(current_user.email, "N/A", "password_change", html_content)
    except Exception:
        pass  # Don't fail if email fails
    
    return {"message": "Password changed successfully"}

@router.post("/change-email")
def change_email_request(
    request: ChangeEmailRequest,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Request to change email address"""
    
    # Verify password
    if not verify_password(request.password, current_user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Password is incorrect"
        )
    
    # Validate new email
    if not validate_email_address(request.new_email):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid email format"
        )
    
    # Check if email is already taken
    existing_user = db.query(User).filter(User.email == request.new_email).first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already in use"
        )
    
    # Generate OTP for email change verification
    otp_code = generate_otp(current_user.id, OTPPurpose.CHANGE_EMAIL, db)
    
    # Send OTP to new email
    html_content = f"""
    <html>
      <body style="font-family: Arial, sans-serif;">
        <h2>Verify Your New Email Address</h2>
        <p>You requested to change your email address to this one.</p>
        <p>Your verification code is: <strong>{otp_code}</strong></p>
        <p>This code will expire in 10 minutes.</p>
      </body>
    </html>
    """
    
    background_tasks.add_task(
        send_otp_email,
        request.new_email,
        otp_code,
        "change_email",
        html_content
    )
    
    # Store pending email change in user session (in real implementation, use Redis or temp storage)
    # For now, we'll store it in a temporary field (you might want to create a separate table for this)
    current_user.temp_new_email = request.new_email
    db.commit()
    
    return {"message": "Verification code sent to your new email address"}

@router.post("/change-phone")
def change_phone_request(
    request: ChangePhoneRequest,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Request to change phone number"""
    
    # Verify password
    if not verify_password(request.password, current_user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Password is incorrect"
        )
    
    # Validate phone number
    if not validate_phone_number(request.new_phone):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid phone number format"
        )
    
    # Check if phone is already taken
    existing_user = db.query(User).filter(User.phone == request.new_phone).first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Phone number already in use"
        )
    
    # Generate OTP for phone change verification
    otp_code = generate_otp(current_user.id, OTPPurpose.CHANGE_PHONE, db)
    
    # In a real implementation, you would send SMS here
    # For now, we'll send email notification
    html_content = f"""
    <html>
      <body style="font-family: Arial, sans-serif;">
        <h2>Verify Your New Phone Number</h2>
        <p>You requested to change your phone number to: {request.new_phone}</p>
        <p>Your verification code is: <strong>{otp_code}</strong></p>
        <p>This code will expire in 10 minutes.</p>
        <p><em>Note: In production, this would be sent via SMS</em></p>
      </body>
    </html>
    """
    
    background_tasks.add_task(
        send_otp_email,
        current_user.email,
        otp_code,
        "change_phone",
        html_content
    )
    
    # Store pending phone change
    current_user.temp_new_phone = request.new_phone
    db.commit()
    
    return {"message": "Verification process started"}

@router.post("/verify-change")
def verify_change(
    request: VerifyChangeRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Verify email or phone change with OTP"""
    
    # Determine OTP purpose
    if request.purpose == "change_email":
        otp_purpose = OTPPurpose.CHANGE_EMAIL
        new_value = current_user.temp_new_email
        field_name = "email"
    elif request.purpose == "change_phone":
        otp_purpose = OTPPurpose.CHANGE_PHONE
        new_value = current_user.temp_new_phone
        field_name = "phone"
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid purpose"
        )
    
    if not new_value:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No pending change request found"
        )
    
    # Verify OTP
    if not verify_otp(current_user.id, request.code, otp_purpose, db):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired verification code"
        )
    
    # Update the field
    if request.purpose == "change_email":
        old_email = current_user.email
        current_user.email = new_value
        current_user.email_verified = True
        current_user.temp_new_email = None
    else:  # change_phone
        current_user.phone = new_value
        current_user.phone_verified = True
        current_user.temp_new_phone = None
    
    db.commit()
    
    # Send confirmation email
    try:
        html_content = f"""
        <html>
          <body style="font-family: Arial, sans-serif;">
            <h2>{field_name.title()} Change Successful</h2>
            <p>Your {field_name} has been successfully updated.</p>
            <p>New {field_name}: <strong>{new_value}</strong></p>
          </body>
        </html>
        """
        send_otp_email(
            current_user.email if request.purpose == "change_phone" else old_email,
            "N/A",
            f"{field_name}_change_success",
            html_content
        )
    except Exception:
        pass  # Don't fail if email fails
    
    return {"message": f"{field_name.title()} changed successfully"}

@router.post("/resend-otp")
def resend_verification_otp(
    request: ResendOTPRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Resend OTP for various purposes"""
    
    purpose_map = {
        "change_email": OTPPurpose.CHANGE_EMAIL,
        "change_phone": OTPPurpose.CHANGE_PHONE,
        "password_reset": OTPPurpose.PASSWORD_RESET,
        "login": OTPPurpose.LOGIN
    }
    
    if request.purpose not in purpose_map:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid OTP purpose"
        )
    
    otp_purpose = purpose_map[request.purpose]
    
    try:
        result = resend_otp(current_user.id, otp_purpose, db)
        return result
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to resend OTP"
        )

@router.put("/language-preference")
def update_language_preference(
    language: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Update user's language preference"""
    
    # Validate language code
    from app.core.i18n import SUPPORTED_LANGUAGES
    if language not in SUPPORTED_LANGUAGES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Unsupported language"
        )
    
    current_user.language_preference = language
    db.commit()
    
    return {"message": f"Language preference updated to {SUPPORTED_LANGUAGES[language]}"}

@router.put("/toggle-two-factor")
def toggle_two_factor(
    enable: bool,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Enable or disable two-factor authentication"""
    
    current_user.two_factor_enabled = enable
    db.commit()
    
    status_text = "enabled" if enable else "disabled"
    return {"message": f"Two-factor authentication {status_text}"}

@router.get("/security-settings", response_model=SecuritySettingsResponse)
def get_security_settings(
    current_user: User = Depends(get_current_user)
):
    """Get user's security settings"""
    
    return {
        "two_factor_enabled": current_user.two_factor_enabled,
        "login_alerts": True,  # Default enabled
        "security_questions_set": bool(current_user.security_questions)
    }
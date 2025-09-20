# app/api/auth.py
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from fastapi.security import OAuth2PasswordRequestForm

from app.db import get_db
from app.schemas.user import UserCreate, UserOut
from app.schemas.otp import OTPVerify
from app.models.user import User
from app.models.otp import OTPPurpose
from app.models.account import Account
from app.core.security import get_password_hash, verify_password, create_access_token
from app.services.utils import generate_account_number
from app.services.otp_service import generate_otp, send_otp_email, verify_otp

router = APIRouter(prefix="/api/v1/auth", tags=["auth"])


# -------------------------------
# Registration
# -------------------------------
@router.post("/register")
def register(user_in: UserCreate, db: Session = Depends(get_db)):
    """Register a new user and send OTP for email verification."""
    existing = db.query(User).filter(User.email == user_in.email).first()
    if existing:
        raise HTTPException(status_code=400, detail="User already exists")

    hashed = get_password_hash(user_in.password)
    user = User(
        email=user_in.email,
        first_name=user_in.first_name,
        last_name=user_in.last_name,
        phone=user_in.phone,
        hashed_password=hashed,
        is_verified=False,
        kyc_status="pending",  # ✅ KYC status field
        is_admin=False,        # ✅ Admin flag
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    # Generate and send OTP for registration
    otp_code = generate_otp(user.id, OTPPurpose.REGISTRATION, db)

    # ✅ Use HTML email template
    html_content = f"""
    <html>
      <body style="font-family: Arial, sans-serif; margin:0; padding:0;">
        <table width="100%" bgcolor="#f9f9f9" cellpadding="0" cellspacing="0" style="padding:20px 0;">
          <tr>
            <td align="center">
              <table width="600" cellpadding="0" cellspacing="0" bgcolor="#ffffff" style="border-radius:8px; overflow:hidden;">
                <tr bgcolor="#004080">
                  <td style="padding:20px; text-align:center;">
                
                  </td>
                </tr>
                <tr>
                  <td style="padding:30px; text-align:center;">
                    <h2 style="color:#333;">Verify Your Email</h2>
                    <p style="color:#555;">Use the OTP below to verify your email address:</p>
                    <p style="font-size:28px; font-weight:bold; color:#004080;">{otp_code}</p>
                    <p style="color:#555;">This code will expire shortly.</p>
                  </td>
                </tr>
                <tr bgcolor="#f1f1f1">
                  <td style="padding:15px; text-align:center; font-size:12px; color:#777;">
                    codeVerification © {2025} 
                  </td>
                </tr>
              </table>
            </td>
          </tr>
        </table>
      </body>
    </html>
    """
    send_otp_email(user.email, otp_code, "registration", html_content=html_content)

    return {"message": "Registration successful. Please verify your email with OTP."}


# -------------------------------
# Verify Registration
# -------------------------------
@router.post("/verify-registration")
def verify_registration(otp_data: OTPVerify, db: Session = Depends(get_db)):
    """Verify OTP for registration and activate account."""
    user = db.query(User).filter(User.email == otp_data.email).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    if user.is_verified:
        raise HTTPException(status_code=400, detail="User already verified")

    # Verify OTP
    if not verify_otp(user.id, otp_data.code, OTPPurpose.REGISTRATION, db):
        raise HTTPException(status_code=400, detail="Invalid or expired OTP")

    # Mark user as verified
    user.is_verified = True

    # Create default account
    acc_num = generate_account_number()
    account = Account(user_id=user.id, account_number=acc_num, balance_cents=0)
    db.add(account)
    db.commit()

    token = create_access_token({"sub": user.email})
    return {
        "access_token": token,
        "token_type": "bearer",
        "message": "Email verified successfully",
    }


# -------------------------------
# Login with OTP
# -------------------------------
@router.post("/login")
def login(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    """Login user and send OTP for 2FA."""
    user = db.query(User).filter(User.email == form_data.username).first()
    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")

    if not user.is_verified:
        raise HTTPException(status_code=400, detail="Please verify your email first")

    # Generate OTP for 2FA login
    otp_code = generate_otp(user.id, OTPPurpose.LOGIN, db)

    # ✅ Use the same HTML template for login OTP
    html_content = f"""
    <html>
      <body style="font-family: Arial, sans-serif; margin:0; padding:0;">
        <table width="100%" bgcolor="#f9f9f9" cellpadding="0" cellspacing="0" style="padding:20px 0;">
          <tr>
            <td align="center">
              <table width="600" cellpadding="0" cellspacing="0" bgcolor="#ffffff" style="border-radius:8px; overflow:hidden;">
                <tr bgcolor="#004080">
                  <td style="padding:20px; text-align:center;">
                    
                  </td>
                </tr>
                <tr>
                  <td style="padding:30px; text-align:center;">
                    <h2 style="color:#333;">Login Verification</h2>
                    <p style="color:#555;">Use the OTP below to complete your login:</p>
                    <p style="font-size:28px; font-weight:bold; color:#004080;">{otp_code}</p>
                  </td>
                </tr>
                <tr bgcolor="#f1f1f1">
                  <td style="padding:15px; text-align:center; font-size:12px; color:#777;">
                    codeVerification © {2025}
                  </td>
                </tr>
              </table>
            </td>
          </tr>
        </table>
      </body>
    </html>
    """
    send_otp_email(user.email, otp_code, "login", html_content=html_content)

    return {"message": "OTP sent to your email. Please verify to complete login."}


# -------------------------------
# Verify Login
# -------------------------------
@router.post("/verify-login")
def verify_login(otp_data: OTPVerify, db: Session = Depends(get_db)):
    """Verify OTP for login and return JWT."""
    user = db.query(User).filter(User.email == otp_data.email).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    if not verify_otp(user.id, otp_data.code, OTPPurpose.LOGIN, db):
        raise HTTPException(status_code=400, detail="Invalid or expired OTP")

    token = create_access_token({"sub": user.email})
    return {
        "access_token": token,
        "token_type": "bearer",
        "user_id": user.id,
        "email": user.email,
    }

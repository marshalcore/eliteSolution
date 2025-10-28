from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form, WebSocket
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime, timedelta
import bcrypt
from passlib.context import CryptContext
import os
import shutil
import uuid

from app.db import get_db
from app.schemas.user import UserCreate, UserOut
from app.schemas.otp import OTPVerify
from app.models.user import User
from app.models.otp import OTPPurpose
from app.models.account import Account
from app.models.card import Card
from app.models.transaction import Transaction
from app.models.withdrawal_account import WithdrawalAccount
from app.core.security import get_password_hash, verify_password, create_access_token, get_current_user
from app.services.utils import generate_account_number
from app.services.otp_service import generate_otp, send_otp_email, verify_otp
from app.services.email_validator import validate_email_address
from app.services.kyc_service import kyc_service
from app.services.marqeta_service import MarqetaService
from app.services.currency_service import CurrencyService
from app.services.trading_service import TradingService

router = APIRouter(
    prefix="/auth",
    tags=["Authentication"]
)

# Create directories for uploads
PROFILE_PICTURES_DIR = "static/profile_pictures"
KYC_DOCUMENTS_DIR = "static/kyc_documents"
os.makedirs(PROFILE_PICTURES_DIR, exist_ok=True)
os.makedirs(KYC_DOCUMENTS_DIR, exist_ok=True)

# Request/Response Models
class LoginRequest(BaseModel):
    email: str
    password: str

class PinLoginRequest(BaseModel):
    email: str
    pin: str

class ForgotPasswordRequest(BaseModel):
    email: str

class ResetPasswordRequest(BaseModel):
    email: str
    code: str
    new_password: str

class TransactionResponse(BaseModel):
    id: str
    date: str
    amount: float
    currency: str
    description: str
    type: str

class DashboardResponse(BaseModel):
    balance: float
    currency: str
    currencySymbol: str
    user: dict
    recentTransactions: List[TransactionResponse]
    kyc_status: str
    can_transact: bool

class ProfileResponse(BaseModel):
    user: dict
    accountDetails: dict
    kyc_status: str
    can_transact: bool

class CardDetailsResponse(BaseModel):
    card_number: str
    cvc: str
    expiry_date: str
    card_holder: str
    balance: float
    currency: str
    currency_symbol: str
    card_type: str = "Visa"

class CardDataResponse(BaseModel):
    card_details: CardDetailsResponse
    recent_transactions: List[TransactionResponse]

class ProfileUpdateRequest(BaseModel):
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    phone: Optional[str] = None

class ProfilePictureResponse(BaseModel):
    message: str
    profile_image_url: str

class UserProfileResponse(BaseModel):
    id: str
    name: str
    username: str
    email: str
    profileImage: str
    first_name: str
    last_name: str
    phone: str
    kyc_status: str
    can_transact: bool
    kyc_details: Optional[dict] = None

class KYCSubmitRequest(BaseModel):
    date_of_birth: str
    address: str
    city: str
    state: str
    country: str
    postal_code: str

class KYCResponse(BaseModel):
    message: str
    kyc_status: str
    can_transact: bool
    missing_documents: Optional[List[str]] = None

class KYCStatusResponse(BaseModel):
    kyc_status: str
    can_transact: bool
    kyc_submitted_at: Optional[str]
    kyc_verified_at: Optional[str]
    kyc_rejection_reason: Optional[str]
    documents: dict
    personal_info_complete: bool

class KYCDocumentStatus(BaseModel):
    id_front: bool
    id_back: bool
    proof_of_address: bool
    selfie: bool

# ✅ NEW: Token Validation Models
class TokenValid(BaseModel):
    valid: bool
    email: Optional[str] = None
    expires_at: Optional[datetime] = None

class RefreshTokenRequest(BaseModel):
    refresh_token: str

class PinSetup(BaseModel):
    pin: str

class PinSetupRequest(BaseModel):
    email: str
    pin: str

class PinVerifyRequest(BaseModel):
    email: str
    pin: str

# ✅ FIXED: Proper password context
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def get_password_hash(password: str) -> str:
    """Hash a password using bcrypt."""
    return pwd_context.hash(password)

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against its hash."""
    return pwd_context.verify(plain_password, hashed_password)

# Utility Functions
def can_user_transact(user: User) -> bool:
    """Check if user can perform transactions based on KYC status"""
    return user.kyc_status == "verified"

def save_uploaded_file(file: UploadFile, directory: str, filename: str) -> str:
    """Save uploaded file and return file path"""
    file_path = os.path.join(directory, filename)
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
    return f"/{directory}/{filename}"

def get_user_kyc_documents_status(user: User) -> dict:
    """Get status of user's KYC documents"""
    return {
        "id_front": bool(user.id_document_front),
        "id_back": bool(user.id_document_back),
        "proof_of_address": bool(user.proof_of_address),
        "selfie": bool(user.selfie_photo)
    }

def get_missing_required_documents(user: User) -> List[str]:
    """Get list of missing required KYC documents"""
    required = ['id_front', 'proof_of_address', 'selfie']
    doc_status = get_user_kyc_documents_status(user)
    return [doc for doc in required if not doc_status.get(doc)]

def is_personal_info_complete(user: User) -> bool:
    """Check if user has completed all personal information"""
    return all([
        user.date_of_birth,
        user.address,
        user.city,
        user.country,
        user.postal_code
    ])

# ✅ NEW: PIN Management Functions
def hash_pin(pin: str) -> str:
    """Hash a PIN using bcrypt"""
    return pwd_context.hash(pin)

def verify_pin(plain_pin: str, hashed_pin: str) -> bool:
    """Verify a PIN against its hash"""
    return pwd_context.verify(plain_pin, hashed_pin)

# ✅ NEW: Token Verification Endpoints
@router.post("/verify-token", response_model=TokenValid)
async def verify_token(current_user: User = Depends(get_current_user)):
    """Validate JWT tokens from frontend"""
    if current_user:
        return TokenValid(
            valid=True,
            email=current_user.email,
            expires_at=datetime.utcnow() + timedelta(hours=24)
        )
    return TokenValid(valid=False)

@router.post("/refresh-token")
async def refresh_token(request: RefreshTokenRequest, db: Session = Depends(get_db)):
    """Implement proper refresh flow"""
    # For now, return error - implement refresh tokens later
    raise HTTPException(
        status_code=501,
        detail="Refresh token flow not implemented yet"
    )

@router.get("/pin/status")
async def get_pin_status(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Check if user has PIN setup"""
    try:
        from app.models.pin import UserPIN
        user_pin = db.query(UserPIN).filter(UserPIN.user_id == current_user.id).first()
        
        return {
            "has_pin": user_pin is not None and user_pin.is_active,
            "is_active": user_pin.is_active if user_pin else False,
            "failed_attempts": user_pin.failed_attempts if user_pin else 0,
            "locked_until": user_pin.locked_until.isoformat() if user_pin and user_pin.locked_until else None
        }
    except ImportError:
        return {"has_pin": False, "is_active": False, "failed_attempts": 0, "locked_until": None}

# ✅ FIXED: PIN Setup Endpoint - Changed hashed_pin to pin_hash
@router.post("/setup-pin")
async def setup_pin(request: PinSetupRequest, db: Session = Depends(get_db)):
    """Setup PIN for user"""
    user = db.query(User).filter(User.email == request.email).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Validate PIN (4-6 digits)
    if not request.pin.isdigit() or len(request.pin) < 4 or len(request.pin) > 6:
        raise HTTPException(status_code=400, detail="PIN must be 4-6 digits")
    
    try:
        from app.models.pin import UserPIN
        
        # Check if PIN already exists
        existing_pin = db.query(UserPIN).filter(UserPIN.user_id == user.id).first()
        
        if existing_pin:
            # Update existing PIN - FIXED: changed hashed_pin to pin_hash
            existing_pin.pin_hash = hash_pin(request.pin)
            existing_pin.is_active = True
            existing_pin.failed_attempts = 0
            existing_pin.locked_until = None
        else:
            # Create new PIN - FIXED: changed hashed_pin to pin_hash
            new_pin = UserPIN(
                user_id=user.id,
                pin_hash=hash_pin(request.pin),  # FIXED: hashed_pin → pin_hash
                is_active=True,
                failed_attempts=0
            )
            db.add(new_pin)
        
        db.commit()
        
        return {"message": "PIN setup successfully"}
        
    except ImportError:
        raise HTTPException(status_code=501, detail="PIN system not implemented")

# ✅ FIXED: PIN Login Endpoint - Changed hashed_pin to pin_hash
@router.post("/login-with-pin")
async def login_with_pin(request: PinLoginRequest, db: Session = Depends(get_db)):
    """Login user with PIN"""
    user = db.query(User).filter(User.email == request.email).first()
    if not user:
        raise HTTPException(status_code=401, detail="Invalid credentials")
    
    if not user.is_verified:
        raise HTTPException(status_code=400, detail="Please verify your email first")
    
    try:
        from app.models.pin import UserPIN
        from datetime import datetime
        
        user_pin = db.query(UserPIN).filter(UserPIN.user_id == user.id).first()
        
        if not user_pin or not user_pin.is_active:
            raise HTTPException(status_code=400, detail="PIN not setup. Please use email login.")
        
        # Check if PIN is locked
        if user_pin.locked_until and user_pin.locked_until > datetime.utcnow():
            raise HTTPException(status_code=423, detail="PIN locked. Try again later.")
        
        # Verify PIN - FIXED: changed hashed_pin to pin_hash
        if not verify_pin(request.pin, user_pin.pin_hash):  # FIXED: hashed_pin → pin_hash
            user_pin.failed_attempts += 1
            
            # Lock after 3 failed attempts
            if user_pin.failed_attempts >= 3:
                user_pin.locked_until = datetime.utcnow() + timedelta(minutes=30)
                db.commit()
                raise HTTPException(status_code=423, detail="Too many failed attempts. PIN locked for 30 minutes.")
            
            db.commit()
            raise HTTPException(status_code=401, detail="Invalid PIN")
        
        # Reset failed attempts on successful login
        user_pin.failed_attempts = 0
        user_pin.locked_until = None
        db.commit()
        
        # Generate token
        token = create_access_token({"sub": user.email})
        return {
            "access_token": token,
            "token_type": "bearer",
            "user_id": user.id,
            "email": user.email,
        }
        
    except ImportError:
        raise HTTPException(status_code=501, detail="PIN system not implemented")

# -------------------------------
# Update Registration to Initialize KYC
# -------------------------------
@router.post("/register")
def register(user_in: UserCreate, db: Session = Depends(get_db)):
    """Register a new user and send OTP for email verification."""

    # ✅ Validate and clean email
    clean_email = validate_email_address(user_in.email)

    existing = db.query(User).filter(User.email == clean_email).first()
    if existing:
        raise HTTPException(status_code=400, detail="User already exists")

    hashed = get_password_hash(user_in.password)
    user = User(
        email=clean_email,
        first_name=user_in.first_name,
        last_name=user_in.last_name,
        phone=user_in.phone,
        hashed_password=hashed,
        is_verified=False,
        kyc_status="pending",  # ✅ Initialize KYC status as pending
        is_admin=False,
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
                  <td style="padding:20px; text-align:center;"></td>
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

    return {
        "message": "Registration successful. Please verify your email with OTP.",
        "kyc_required": True,  # ✅ Inform frontend that KYC is required
        "kyc_status": "pending"
    }

# -------------------------------
# Login with OTP
# -------------------------------
# In your app/api/auth.py - ONLY FIXED THE TIMEOUT ISSUE
@router.post("/login")
def login(login_data: LoginRequest, db: Session = Depends(get_db)):
    """Login user and send OTP for 2FA."""

    # ✅ Validate email from login form
    clean_email = validate_email_address(login_data.email)
    print(f"🔍 Login attempt for: {clean_email}")

    try:
        # ✅ FIX: Use raw SQL to avoid relationship mapping issues
        from sqlalchemy import text
        result = db.execute(
            text("SELECT * FROM users WHERE email = :email"), 
            {"email": clean_email}
        ).first()
        
        if not result:
            print(f"❌ User not found: {clean_email}")
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")

        # Convert result to dictionary
        user_dict = dict(result)
        
        print(f"✅ User found: {user_dict['email']}")
        print(f"📊 User verification status: {user_dict['is_verified']}")
        
        # Check password separately for debugging
        password_valid = verify_password(login_data.password, user_dict['hashed_password'])
        print(f"🔑 Password valid: {password_valid}")
        
        if not password_valid:
            print(f"❌ Invalid password for user: {clean_email}")
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")

        if not user_dict['is_verified']:
            raise HTTPException(status_code=400, detail="Please verify your email first")

        # ✅ Generate OTP for 2FA login
        print(f"🎯 Generating OTP for purpose: {OTPPurpose.LOGIN}")
        otp_code = generate_otp(user_dict['id'], OTPPurpose.LOGIN, db)
        print(f"✅ OTP generated: {otp_code}")

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
                        <h1 style="color:white; margin:0;">EliteSolution</h1>
                      </td>
                    </tr>
                    <tr>
                      <td style="padding:30px; text-align:center;">
                        <h2 style="color:#333;">Login Verification</h2>
                        <p style="color:#555;">Use the OTP below to complete your login:</p>
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
        
        # ✅ Send OTP email - NO COMPLEX TIMEOUT, JUST TRY IT
        email_sent = send_otp_email(clean_email, otp_code, "login", html_content=html_content)
        
        if email_sent:
            print(f"📧 OTP email sent to: {clean_email}")
            return {"message": "OTP sent to your email. Please verify to complete login."}
        else:
            # If email fails but OTP was generated, return success with console message
            print(f"⚠️ Email failed but OTP generated: {otp_code}")
            return {"message": "OTP generated. Please check your console for the code.", "otp_code": otp_code}
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ Login error: {e}")
        raise HTTPException(status_code=500, detail="Login failed")
# -------------------------------
# Verify Login
# -------------------------------
@router.post("/verify-login")
def verify_login(otp_data: OTPVerify, db: Session = Depends(get_db)):
    """Verify OTP for login and return JWT."""

    # ✅ Validate email from OTP payload
    clean_email = validate_email_address(otp_data.email)

    user = db.query(User).filter(User.email == clean_email).first()
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

# -------------------------------
# Forgot Password
# -------------------------------
@router.post("/forgot-password")
def forgot_password(request: ForgotPasswordRequest, db: Session = Depends(get_db)):
    """Send password reset OTP to user's email."""
    
    clean_email = validate_email_address(request.email)
    print(f"🔍 Forgot password request for: {clean_email}")

    user = db.query(User).filter(User.email == clean_email).first()
    if not user:
        print(f"❌ User not found for password reset: {clean_email}")
        # Don't reveal that user doesn't exist for security
        return {"message": "If the email exists, password reset instructions have been sent."}

    # Generate OTP for password reset
    otp_code = generate_otp(user.id, OTPPurpose.PASSWORD_RESET, db)
    print(f"✅ Password reset OTP generated: {otp_code}")

    # Send OTP email
    html_content = f"""
    <html>
      <body style="font-family: Arial, sans-serif; margin:0; padding:0;">
        <table width="100%" bgcolor="#f9f9f9" cellpadding="0" cellspacing="0" style="padding:20px 0;">
          <tr>
            <td align="center">
              <table width="600" cellpadding="0" cellspacing="0" bgcolor="#ffffff" style="border-radius:8px; overflow:hidden;">
                <tr bgcolor="#004080">
                  <td style="padding:20px; text-align:center;"></td>
                </tr>
                <tr>
                  <td style="padding:30px; text-align:center;">
                    <h2 style="color:#333;">Password Reset</h2>
                    <p style="color:#555;">Use the OTP below to reset your password:</p>
                    <p style="font-size:28px; font-weight=bold; color:#004080;">{otp_code}</p>
                    <p style="color:#555;">This code will expire shortly.</p>
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
    
    send_otp_email(user.email, otp_code, "password reset", html_content=html_content)
    print(f"📧 Password reset email sent to: {clean_email}")

    return {"message": "If the email exists, password reset instructions have been sent."}

# -------------------------------
# Reset Password
# -------------------------------
@router.post("/reset-password")
def reset_password(request: ResetPasswordRequest, db: Session = Depends(get_db)):
    """Reset password after OTP verification."""
    
    clean_email = validate_email_address(request.email)
    print(f"🔍 Password reset attempt for: {clean_email}")

    user = db.query(User).filter(User.email == clean_email).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # Verify OTP for password reset
    if not verify_otp(user.id, request.code, OTPPurpose.PASSWORD_RESET, db):
        raise HTTPException(status_code=400, detail="Invalid or expired OTP")

    # Update password
    user.hashed_password = get_password_hash(request.new_password)
    db.commit()

    print(f"✅ Password reset successful for: {clean_email}")
    return {"message": "Password reset successfully. You can now login with your new password."}

# ADD TO EXISTING app/api/auth.py
@router.post("/verify-registration")
def verify_registration(otp_data: OTPVerify, db: Session = Depends(get_db)):
    """Verify OTP for registration and activate account."""

    clean_email = validate_email_address(otp_data.email)

    user = db.query(User).filter(User.email == clean_email).first()
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

    # ✅ NEW: Don't return token immediately, redirect to PIN setup
    return {
        "message": "Email verified successfully. Please setup your security PIN.",
        "requires_pin_setup": True,  # ✅ NEW: Frontend will redirect to PIN setup
        "email": user.email
    }

# -------------------------------
# Update Registration to Initialize KYC
# -------------------------------
@router.post("/register")
def register(user_in: UserCreate, db: Session = Depends(get_db)):
    """Register a new user and send OTP for email verification."""

    # ✅ Validate and clean email
    clean_email = validate_email_address(user_in.email)

    existing = db.query(User).filter(User.email == clean_email).first()
    if existing:
        raise HTTPException(status_code=400, detail="User already exists")

    hashed = get_password_hash(user_in.password)
    user = User(
        email=clean_email,
        first_name=user_in.first_name,
        last_name=user_in.last_name,
        phone=user_in.phone,
        hashed_password=hashed,
        is_verified=False,
        kyc_status="pending",  # ✅ Initialize KYC status as pending
        is_admin=False,
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
                  <td style="padding:20px; text-align:center;"></td>
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

    return {
        "message": "Registration successful. Please verify your email with OTP.",
        "kyc_required": True,  # ✅ Inform frontend that KYC is required
        "kyc_status": "pending"
    }

# -------------------------------
# Login with OTP
# -------------------------------
# In your app/api/auth.py - ONLY FIXED THE TIMEOUT ISSUE
@router.post("/login")
def login(login_data: LoginRequest, db: Session = Depends(get_db)):
    """Login user and send OTP for 2FA."""

    # ✅ Validate email from login form
    clean_email = validate_email_address(login_data.email)
    print(f"🔍 Login attempt for: {clean_email}")

    try:
        # ✅ FIX: Use raw SQL to avoid relationship mapping issues
        from sqlalchemy import text
        result = db.execute(
            text("SELECT * FROM users WHERE email = :email"), 
            {"email": clean_email}
        ).first()
        
        if not result:
            print(f"❌ User not found: {clean_email}")
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")

        # Convert result to dictionary
        user_dict = dict(result)
        
        print(f"✅ User found: {user_dict['email']}")
        print(f"📊 User verification status: {user_dict['is_verified']}")
        
        # Check password separately for debugging
        password_valid = verify_password(login_data.password, user_dict['hashed_password'])
        print(f"🔑 Password valid: {password_valid}")
        
        if not password_valid:
            print(f"❌ Invalid password for user: {clean_email}")
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")

        if not user_dict['is_verified']:
            raise HTTPException(status_code=400, detail="Please verify your email first")

        # ✅ Generate OTP for 2FA login
        print(f"🎯 Generating OTP for purpose: {OTPPurpose.LOGIN}")
        otp_code = generate_otp(user_dict['id'], OTPPurpose.LOGIN, db)
        print(f"✅ OTP generated: {otp_code}")

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
                        <h1 style="color:white; margin:0;">EliteSolution</h1>
                      </td>
                    </tr>
                    <tr>
                      <td style="padding:30px; text-align:center;">
                        <h2 style="color:#333;">Login Verification</h2>
                        <p style="color:#555;">Use the OTP below to complete your login:</p>
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
        
        # ✅ Send OTP email - NO COMPLEX TIMEOUT, JUST TRY IT
        email_sent = send_otp_email(clean_email, otp_code, "login", html_content=html_content)
        
        if email_sent:
            print(f"📧 OTP email sent to: {clean_email}")
            return {"message": "OTP sent to your email. Please verify to complete login."}
        else:
            # If email fails but OTP was generated, return success with console message
            print(f"⚠️ Email failed but OTP generated: {otp_code}")
            return {"message": "OTP generated. Please check your console for the code.", "otp_code": otp_code}
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ Login error: {e}")
        raise HTTPException(status_code=500, detail="Login failed")
# -------------------------------
# Verify Login
# -------------------------------
@router.post("/verify-login")
def verify_login(otp_data: OTPVerify, db: Session = Depends(get_db)):
    """Verify OTP for login and return JWT."""

    # ✅ Validate email from OTP payload
    clean_email = validate_email_address(otp_data.email)

    user = db.query(User).filter(User.email == clean_email).first()
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

# -------------------------------
# Forgot Password
# -------------------------------
@router.post("/forgot-password")
def forgot_password(request: ForgotPasswordRequest, db: Session = Depends(get_db)):
    """Send password reset OTP to user's email."""
    
    clean_email = validate_email_address(request.email)
    print(f"🔍 Forgot password request for: {clean_email}")

    user = db.query(User).filter(User.email == clean_email).first()
    if not user:
        print(f"❌ User not found for password reset: {clean_email}")
        # Don't reveal that user doesn't exist for security
        return {"message": "If the email exists, password reset instructions have been sent."}

    # Generate OTP for password reset
    otp_code = generate_otp(user.id, OTPPurpose.PASSWORD_RESET, db)
    print(f"✅ Password reset OTP generated: {otp_code}")

    # Send OTP email
    html_content = f"""
    <html>
      <body style="font-family: Arial, sans-serif; margin:0; padding:0;">
        <table width="100%" bgcolor="#f9f9f9" cellpadding="0" cellspacing="0" style="padding:20px 0;">
          <tr>
            <td align="center">
              <table width="600" cellpadding="0" cellspacing="0" bgcolor="#ffffff" style="border-radius:8px; overflow:hidden;">
                <tr bgcolor="#004080">
                  <td style="padding:20px; text-align:center;"></td>
                </tr>
                <tr>
                  <td style="padding:30px; text-align:center;">
                    <h2 style="color:#333;">Password Reset</h2>
                    <p style="color:#555;">Use the OTP below to reset your password:</p>
                    <p style="font-size:28px; font-weight=bold; color:#004080;">{otp_code}</p>
                    <p style="color:#555;">This code will expire shortly.</p>
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
    
    send_otp_email(user.email, otp_code, "password reset", html_content=html_content)
    print(f"📧 Password reset email sent to: {clean_email}")

    return {"message": "If the email exists, password reset instructions have been sent."}

# -------------------------------
# Reset Password
# -------------------------------
@router.post("/reset-password")
def reset_password(request: ResetPasswordRequest, db: Session = Depends(get_db)):
    """Reset password after OTP verification."""
    
    clean_email = validate_email_address(request.email)
    print(f"🔍 Password reset attempt for: {clean_email}")

    user = db.query(User).filter(User.email == clean_email).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # Verify OTP for password reset
    if not verify_otp(user.id, request.code, OTPPurpose.PASSWORD_RESET, db):
        raise HTTPException(status_code=400, detail="Invalid or expired OTP")

    # Update password
    user.hashed_password = get_password_hash(request.new_password)
    db.commit()

    print(f"✅ Password reset successful for: {clean_email}")
    return {"message": "Password reset successfully. You can now login with your new password."}

# ADD TO EXISTING app/api/auth.py
@router.post("/verify-registration")
def verify_registration(otp_data: OTPVerify, db: Session = Depends(get_db)):
    """Verify OTP for registration and activate account."""

    clean_email = validate_email_address(otp_data.email)

    user = db.query(User).filter(User.email == clean_email).first()
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

    # ✅ NEW: Don't return token immediately, redirect to PIN setup
    return {
        "message": "Email verified successfully. Please setup your security PIN.",
        "requires_pin_setup": True,  # ✅ NEW: Frontend will redirect to PIN setup
        "email": user.email
    }

@router.post("/start-trading")
async def start_trading(
    amount: float = Form(...),
    strategy: str = Form(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Start automated trading bot"""
    
    if current_user.kyc_status != "verified":
        raise HTTPException(status_code=403, detail="KYC verification required for trading")
    
    trading_service = TradingService()
    
    try:
        result = await trading_service.start_trading_bot(
            current_user.id, amount, strategy, db
        )
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to start trading: {str(e)}")

@router.get("/test-marqeta")
async def test_marqeta_connection(current_user: User = Depends(get_current_user)):
    """Test Marqeta API connection"""
    marqeta_service = MarqetaService()
    
    try:
        connection_ok = await marqeta_service.test_connection()
        if connection_ok:
            return {"status": "success", "message": "Marqeta connection successful"}
        else:
            return {"status": "error", "message": "Marqeta connection failed"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Marqeta test failed: {str(e)}")

@router.post("/generate-virtual-card")
async def generate_virtual_card(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Auto-generate virtual card via Marqeta after KYC verification"""
    
    if current_user.kyc_status != "verified":
        raise HTTPException(status_code=403, detail="KYC verification required")
    
    # Check if user already has a card
    existing_card = db.query(Card).filter(Card.user_id == current_user.id).first()
    if existing_card:
        return {
            "message": "Virtual card already exists",
            "card": {
                "last_four": existing_card.card_number[-4:],
                "expiry_date": existing_card.expiry_date,
                "card_holder": existing_card.card_holder_name
            }
        }
    
    # Generate card via Marqeta
    marqeta_service = MarqetaService()
    
    try:
        # 1. Create user in Marqeta
        user_data = {
            "user_id": current_user.id,
            "first_name": current_user.first_name,
            "last_name": current_user.last_name,
            "email": current_user.email
        }
        marqeta_user = await marqeta_service.create_user(user_data)
        
        # 2. Create virtual card
        card_data = {
            "user_id": current_user.id,
            "first_name": current_user.first_name,
            "last_name": current_user.last_name
        }
        marqeta_card = await marqeta_service.create_virtual_card(
            marqeta_user['token'], 
            card_data
        )
        
        # 3. Save card to database
        new_card = Card(
            user_id=current_user.id,
            card_number=marqeta_card.get('pan', '####-####-####-####'),  # Use placeholder if no PAN
            card_holder_name=f"{current_user.first_name} {current_user.last_name}",
            expiry_date=marqeta_card.get('expiration', 'MM/YY'),
            cvv=marqeta_card.get('cvv_number', '***'),
            marqeta_card_token=marqeta_card['token'],
            marqeta_user_token=marqeta_user['token'],
            linked_to_vault=True
        )
        
        db.add(new_card)
        db.commit()
        db.refresh(new_card)
        
        return {
            "message": "Virtual card generated successfully",
            "card": {
                "last_four": marqeta_card.get('last_four', '####'),
                "expiry_date": marqeta_card.get('expiration', 'MM/YY'),
                "card_holder": f"{current_user.first_name} {current_user.last_name}",
                "type": "Virtual Mastercard",
                "linked_to_vault": True,
                "marqeta_token": marqeta_card['token']
            }
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to generate virtual card: {str(e)}")

# ✅ NEW: WebSocket for real-time transaction updates
@router.websocket("/ws/transaction-status/{tx_id}")
async def transaction_status(websocket: WebSocket, tx_id: str):
    """WebSocket for real-time transaction updates"""
    await websocket.accept()
    try:
        while True:
            # Send initial status
            await websocket.send_text(json.dumps({"status": "connected", "transaction_id": tx_id}))
            
            # Simulate status updates
            import asyncio
            import json
            statuses = ["processing", "verifying", "completed", "failed"]
            for status in statuses:
                await asyncio.sleep(2)
                await websocket.send_text(json.dumps({
                    "transaction_id": tx_id,
                    "status": status,
                    "timestamp": datetime.utcnow().isoformat()
                }))
                if status == "completed" or status == "failed":
                    break
                    
    except Exception as e:
        print(f"WebSocket error for transaction {tx_id}: {e}")
    finally:
        await websocket.close()

# app/api/auth.py - ADD/UPDATE THESE ENDPOINTS
@router.get("/exchange-rates")
async def get_exchange_rates(current_user: User = Depends(get_current_user)):
    """Get current exchange rates for all supported currencies including crypto"""
    currency_service = CurrencyService()
    rates = await currency_service.get_exchange_rates()
    supported_currencies = await currency_service.get_supported_currencies()
    
    # Get currency information
    currency_info = {}
    for currency in supported_currencies:
        info = await currency_service.get_currency_info(currency)
        currency_info[currency] = info
    
    return {
        "base_currency": "USD",
        "rates": {curr: rates[curr] for curr in supported_currencies},
        "currency_info": currency_info,
        "last_updated": datetime.utcnow().isoformat()
    }

@router.get("/convert-currency")
async def convert_currency(
    amount: float,
    from_currency: str,
    to_currency: str,
    current_user: User = Depends(get_current_user)
):
    """Convert amount between currencies"""
    currency_service = CurrencyService()
    
    # Validate currencies
    supported_currencies = await currency_service.get_supported_currencies()
    if from_currency not in supported_currencies:
        raise HTTPException(status_code=400, detail=f"Unsupported source currency: {from_currency}")
    if to_currency not in supported_currencies:
        raise HTTPException(status_code=400, detail=f"Unsupported target currency: {to_currency}")
    
    try:
        converted_amount = await currency_service.convert_amount(amount, from_currency, to_currency)
        
        from_info = await currency_service.get_currency_info(from_currency)
        to_info = await currency_service.get_currency_info(to_currency)
        
        return {
            "original_amount": amount,
            "original_currency": from_currency,
            "converted_amount": converted_amount,
            "converted_currency": to_currency,
            "exchange_rate": converted_amount / amount if amount > 0 else 0,
            "currency_info": {
                "from": from_info,
                "to": to_info
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Conversion failed: {str(e)}")


# -------------------------------
# Dashboard Route
# -------------------------------
@router.get("/dashboard", response_model=DashboardResponse)
def get_user_dashboard(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Get user dashboard data with KYC status"""
    
    try:
        # Get user's account
        account = db.query(Account).filter(Account.user_id == current_user.id).first()
        if not account:
            raise HTTPException(status_code=404, detail="Account not found")

        profile_image = getattr(current_user, 'profile_image', None) or "/images/profile.jpg"

        user_data = {
            "id": current_user.id,
            "name": f"{current_user.first_name} {current_user.last_name}",
            "username": f"@{current_user.first_name[0].lower()}.{current_user.last_name.lower()}",
            "profileImage": profile_image
        }

        # Get recent transactions
        transactions = db.query(Transaction).filter(
            (Transaction.from_account_id == account.id) | 
            (Transaction.to_account_id == account.id)
        ).order_by(Transaction.created_at.desc()).limit(5).all()

        recent_transactions = []
        for txn in transactions:
            is_debit = txn.from_account_id == account.id
            recent_transactions.append({
                "id": str(txn.id),
                "date": txn.created_at.strftime("%b %d") if txn.created_at else "May 6",
                "amount": (txn.amount_cents / 100) * (-1 if is_debit else 1),
                "currency": account.currency,
                "description": txn.extra_data.get("description", f"{txn.type.title()}") if txn.extra_data else f"{txn.type.title()}",
                "type": "debit" if is_debit else "credit"
            })

        # If no transactions, provide sample data
        if not recent_transactions:
            recent_transactions = [
                {
                    "id": "1",
                    "date": "May 6",
                    "amount": -127.78,
                    "currency": "USD",
                    "description": "Online Purchase",
                    "type": "debit"
                },
                {
                    "id": "2", 
                    "date": "May 5",
                    "amount": -970.23,
                    "currency": "USD",
                    "description": "Bank Transfer",
                    "type": "debit"
                }
            ]

        return {
            "balance": account.balance_cents / 100,
            "currency": "USD",
            "currencySymbol": "$",
            "user": user_data,
            "recentTransactions": recent_transactions,
            "kyc_status": current_user.kyc_status,
            "can_transact": can_user_transact(current_user)
        }
        
    except Exception as e:
        print(f"❌ Error in dashboard: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

# -------------------------------
# Profile Route
# -------------------------------
@router.get("/profile", response_model=ProfileResponse)
def get_user_profile_route(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Get user profile information with KYC status"""
    
    try:
        account = db.query(Account).filter(Account.user_id == current_user.id).first()
        if not account:
            raise HTTPException(status_code=404, detail="Account not found")

        profile_image = getattr(current_user, 'profile_image', None) or "/images/profile.jpg"

        user_data = {
            "id": current_user.id,
            "name": f"{current_user.first_name} {current_user.last_name}",
            "username": f"@{current_user.first_name[0].lower()}.{current_user.last_name.lower()}",
            "email": current_user.email,
            "profileImage": profile_image,
            "inboxCount": 4
        }

        account_details = {
            "accountNumber": account.account_number,
            "accountType": "Premium",
            "memberSince": "2024",
            "status": "Active"
        }

        return {
            "user": user_data,
            "accountDetails": account_details,
            "kyc_status": current_user.kyc_status,
            "can_transact": can_user_transact(current_user)
        }
        
    except Exception as e:
        print(f"❌ Error in profile route: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

# -------------------------------
# Transactions Route
# -------------------------------
@router.get("/transactions", response_model=List[TransactionResponse])
def get_user_transactions(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Get user transaction history."""
    
    try:
        account = db.query(Account).filter(Account.user_id == current_user.id).first()
        if not account:
            raise HTTPException(status_code=404, detail="Account not found")

        # Get transactions
        transactions = db.query(Transaction).filter(
            (Transaction.from_account_id == account.id) | 
            (Transaction.to_account_id == account.id)
        ).order_by(Transaction.created_at.desc()).limit(10).all()

        transaction_list = []
        for txn in transactions:
            is_debit = txn.from_account_id == account.id
            transaction_list.append({
                "id": str(txn.id),
                "date": txn.created_at.strftime("%b %d") if txn.created_at else "May 6",
                "amount": (txn.amount_cents / 100) * (-1 if is_debit else 1),
                "currency": account.currency,
                "description": txn.extra_data.get("description", f"{txn.type.title()}") if txn.extra_data else f"{txn.type.title()}",
                "type": "debit" if is_debit else "credit"
            })

        # If no transactions, provide sample data
        if not transaction_list:
            transaction_list = [
                {
                    "id": "1",
                    "date": "May 6",
                    "amount": -127.78,
                    "currency": "USD",
                    "description": "Online Shopping",
                    "type": "debit"
                },
                {
                    "id": "2",
                    "date": "May 5", 
                    "amount": -970.23,
                    "currency": "USD",
                    "description": "Wire Transfer",
                    "type": "debit"
                }
            ]

        return transaction_list
        
    except Exception as e:
        print(f"❌ Error getting transactions: {e}")
        raise HTTPException(status_code=500, detail="Failed to get transactions")

# -------------------------------
# KYC Document Upload Route (Enhanced)
# -------------------------------
@router.post("/upload-kyc-document", response_model=KYCResponse)
async def upload_kyc_document(
    document_type: str = Form(...),
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Upload KYC documents for verification with enhanced validation"""
    
    try:
        # Validate document type
        allowed_types = ['id_front', 'id_back', 'proof_of_address', 'selfie']
        if document_type not in allowed_types:
            raise HTTPException(
                status_code=400, 
                detail=f"Invalid document type. Allowed types: {', '.join(allowed_types)}"
            )
        
        # Validate document using KYC service
        validation_result = await kyc_service.validate_kyc_document(file, document_type)
        
        # Generate unique filename with UUID for security
        file_extension = os.path.splitext(file.filename.lower())[1]
        unique_id = uuid.uuid4().hex[:8]
        filename = f"user_{current_user.id}_{document_type}_{unique_id}_{int(datetime.now().timestamp())}{file_extension}"
        file_url = save_uploaded_file(file, KYC_DOCUMENTS_DIR, filename)
        
        # Update user's KYC document in database
        if document_type == 'id_front':
            current_user.id_document_front = file_url
        elif document_type == 'id_back':
            current_user.id_document_back = file_url
        elif document_type == 'proof_of_address':
            current_user.proof_of_address = file_url
        elif document_type == 'selfie':
            current_user.selfie_photo = file_url
        
        db.commit()
        
        print(f"✅ KYC document uploaded for user: {current_user.email}, type: {document_type}")
        
        # Check if user can now submit KYC
        missing_docs = get_missing_required_documents(current_user)
        
        return {
            "message": f"{document_type.replace('_', ' ').title()} uploaded successfully",
            "kyc_status": current_user.kyc_status,
            "can_transact": can_user_transact(current_user),
            "missing_documents": missing_docs if missing_docs else None
        }
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ Error uploading KYC document: {e}")
        raise HTTPException(status_code=500, detail="Failed to upload KYC document")

# -------------------------------
# Submit KYC Application (Enhanced)
# -------------------------------
@router.post("/submit-kyc", response_model=KYCResponse)
async def submit_kyc_application(
    kyc_data: KYCSubmitRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Submit KYC application for verification with comprehensive validation"""
    
    try:
        # Check if user is already verified
        if current_user.kyc_status == "verified":
            raise HTTPException(
                status_code=400,
                detail="Your KYC is already verified"
            )
        
        # Check if user is already submitted
        if current_user.kyc_status == "submitted":
            raise HTTPException(
                status_code=400,
                detail="Your KYC application is already under review"
            )
        
        # Validate personal information using KYC service
        kyc_service.validate_personal_info(kyc_data.dict())
        
        # Check if all required documents are uploaded
        missing_docs = get_missing_required_documents(current_user)
        if missing_docs:
            raise HTTPException(
                status_code=400,
                detail={
                    "message": "Missing required documents",
                    "missing_documents": missing_docs
                }
            )
        
        # Update user's KYC information
        current_user.date_of_birth = datetime.strptime(kyc_data.date_of_birth, "%Y-%m-%d")
        current_user.address = kyc_data.address
        current_user.city = kyc_data.city
        current_user.state = kyc_data.state
        current_user.country = kyc_data.country
        current_user.postal_code = kyc_data.postal_code
        
        # Update KYC status
        current_user.kyc_status = "submitted"
        current_user.kyc_submitted_at = datetime.now()
        current_user.kyc_rejection_reason = None  # Clear any previous rejection
        
        db.commit()
        
        print(f"✅ KYC application submitted for user: {current_user.email}")
        
        # TODO: In production, you would:
        # 1. Send notification to admin for review
        # 2. Trigger automated verification process
        # 3. Send email confirmation to user
        
        return {
            "message": "KYC application submitted successfully. Your documents are under review. This may take 1-2 business days.",
            "kyc_status": current_user.kyc_status,
            "can_transact": can_user_transact(current_user)
        }
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail="Invalid date format. Use YYYY-MM-DD.")
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ Error submitting KYC application: {e}")
        raise HTTPException(status_code=500, detail="Failed to submit KYC application")

# -------------------------------
# Get KYC Status (Enhanced)
# -------------------------------
@router.get("/kyc-status", response_model=KYCStatusResponse)
def get_kyc_status(
    current_user: User = Depends(get_current_user)
):
    """Get user's comprehensive KYC status"""
    
    documents_status = get_user_kyc_documents_status(current_user)
    personal_info_complete = is_personal_info_complete(current_user)
    
    return {
        "kyc_status": current_user.kyc_status,
        "can_transact": can_user_transact(current_user),
        "kyc_submitted_at": current_user.kyc_submitted_at.isoformat() if current_user.kyc_submitted_at else None,
        "kyc_verified_at": current_user.kyc_verified_at.isoformat() if current_user.kyc_verified_at else None,
        "kyc_rejection_reason": current_user.kyc_rejection_reason,
        "documents": documents_status,
        "personal_info_complete": personal_info_complete
    }

# -------------------------------
# KYC Document Status
# -------------------------------
@router.get("/kyc-documents-status", response_model=KYCDocumentStatus)
def get_kyc_documents_status(
    current_user: User = Depends(get_current_user)
):
    """Get status of user's KYC documents"""
    return get_user_kyc_documents_status(current_user)

# -------------------------------
# Profile Picture Upload Route
# -------------------------------
@router.post("/upload-profile-picture", response_model=ProfilePictureResponse)
async def upload_profile_picture(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Upload and update user's profile picture."""
    
    try:
        # Validate file type
        allowed_extensions = {'.jpg', '.jpeg', '.png', '.gif'}
        file_extension = os.path.splitext(file.filename)[1].lower()
        
        if file_extension not in allowed_extensions:
            raise HTTPException(
                status_code=400, 
                detail="Invalid file type. Only JPG, JPEG, PNG, and GIF are allowed."
            )
        
        # Validate file size (max 5MB)
        max_size = 5 * 1024 * 1024
        file_contents = await file.read()
        if len(file_contents) > max_size:
            raise HTTPException(
                status_code=400,
                detail="File too large. Maximum size is 5MB."
            )
        
        # Reset file pointer
        file.file.seek(0)
        
        # Generate unique filename with UUID
        unique_id = uuid.uuid4().hex[:8]
        filename = f"user_{current_user.id}_profile_{unique_id}_{int(datetime.now().timestamp())}{file_extension}"
        file_url = save_uploaded_file(file, PROFILE_PICTURES_DIR, filename)
        
        # Update user's profile picture in database
        current_user.profile_image = file_url
        db.commit()
        
        print(f"✅ Profile picture updated for user: {current_user.email}")
        
        return {
            "message": "Profile picture updated successfully",
            "profile_image_url": file_url
        }
        
    except Exception as e:
        print(f"❌ Error uploading profile picture: {e}")
        raise HTTPException(status_code=500, detail="Failed to upload profile picture")

# -------------------------------
# Get User Profile (Enhanced with KYC Details)
# -------------------------------
@router.get("/user-profile", response_model=UserProfileResponse)
def get_user_profile(current_user: User = Depends(get_current_user)):
    """Get detailed user profile information with KYC status"""
    
    try:
        profile_image = getattr(current_user, 'profile_image', None) or "/images/profile.jpg"
        
        # Get KYC details
        kyc_details = {
            "documents_uploaded": get_user_kyc_documents_status(current_user),
            "personal_info_complete": is_personal_info_complete(current_user),
            "missing_documents": get_missing_required_documents(current_user),
            "can_submit_kyc": kyc_service.check_kyc_completion(current_user)
        }
        
        return {
            "id": str(current_user.id),
            "name": f"{current_user.first_name} {current_user.last_name}",
            "username": f"@{current_user.first_name[0].lower()}.{current_user.last_name.lower()}",
            "email": current_user.email,
            "profileImage": profile_image,
            "first_name": current_user.first_name,
            "last_name": current_user.last_name,
            "phone": current_user.phone,
            "kyc_status": current_user.kyc_status,
            "can_transact": can_user_transact(current_user),
            "kyc_details": kyc_details
        }
        
    except Exception as e:
        print(f"❌ Error getting user profile: {e}")
        raise HTTPException(status_code=500, detail="Failed to get user profile")

# -------------------------------
# Transaction Check Middleware
# -------------------------------
def check_kyc_for_transaction(current_user: User, operation: str = "transaction"):
    """Middleware to check KYC status before allowing transactions"""
    if not can_user_transact(current_user):
        error_messages = {
            "pending": "KYC verification required. Please complete your KYC verification to perform transactions.",
            "submitted": "KYC verification in progress. Your documents are under review. You cannot perform transactions until verification is complete.",
            "rejected": f"KYC verification rejected. {current_user.kyc_rejection_reason or 'Please contact support or resubmit your documents.'}"
        }
        
        message = error_messages.get(current_user.kyc_status, "KYC verification required.")
        
        raise HTTPException(
            status_code=403,
            detail=message
        )

# -------------------------------
# Update Card Details with KYC Check
# -------------------------------
@router.get("/card-details", response_model=CardDataResponse)
def get_card_details(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Get complete card details for the Cards page."""
    
    try:
        # KYC check for card operations
        check_kyc_for_transaction(current_user, "card operations")
        
        account = db.query(Account).filter(Account.user_id == current_user.id).first()
        if not account:
            raise HTTPException(status_code=404, detail="Account not found")

        card_number = f"5244 2150 {account.account_number[-4:]} {account.account_number[-8:-4]}"
        cvc = account.account_number[-3:]
        
        expiry_year = datetime.now().year + 10
        expiry_date = f"10/{expiry_year % 100}"
        
        card_holder = f"{current_user.first_name} {current_user.last_name}"

        transactions = [
            {
                "id": "1",
                "date": "May 6",
                "amount": -127.78,
                "currency": "USD",
                "description": "Online Shopping",
                "type": "debit"
            },
            {
                "id": "2",
                "date": "May 5", 
                "amount": -970.23,
                "currency": "USD",
                "description": "Wire Transfer", 
                "type": "debit"
            }
        ]

        return {
            "card_details": {
                "card_number": card_number,
                "cvc": cvc,
                "expiry_date": expiry_date,
                "card_holder": card_holder,
                "balance": account.balance_cents / 100,
                "currency": "USD",
                "currency_symbol": "$",
                "card_type": "Visa"
            },
            "recent_transactions": transactions
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail="Internal server error")
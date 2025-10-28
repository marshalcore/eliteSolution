# app/api/pin.py - COMPLETE UPDATED VERSION
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
from pydantic import BaseModel
import bcrypt

# ✅ FIXED: Import get_db from correct location
from app.db.database import get_db
from app.models.user import User
from app.core.security import get_current_user, create_access_token
from app.models.otp import OTPPurpose
from app.services.otp_service import generate_otp, verify_otp, send_otp_email

# ✅ FIXED: Import PIN-related models with proper error handling
try:
    from app.models.pin import UserPIN
    from app.schemas.pin import PINCreate, PINVerify, PINResponse, PINStatus
except ImportError:
    # Fallback implementations
    from pydantic import BaseModel
    
    class PINCreate(BaseModel):
        pin: str

    class PINVerify(BaseModel):
        pin: str
        email: str

    class PINResponse(BaseModel):
        message: str
        pin_set: bool
        created_at: datetime

    class PINStatus(BaseModel):
        has_pin: bool
        is_active: bool
        failed_attempts: int
        locked_until: datetime = None
        last_used: datetime = None

# ✅ NEW: PIN Reset Models
class ForgotPINRequest(BaseModel):
    email: str

class ResetPINRequest(BaseModel):
    email: str
    code: str
    new_pin: str

# ✅ FIXED: Security functions
def get_pin_hash(pin: str) -> str:
    """Hash a PIN using bcrypt"""
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(pin.encode('utf-8'), salt).decode('utf-8')

def verify_pin(plain_pin: str, pin_hash: str) -> bool:
    """Verify a PIN against its hash"""
    try:
        return bcrypt.checkpw(plain_pin.encode('utf-8'), pin_hash.encode('utf-8'))
    except Exception:
        return False

def is_pin_locked(failed_attempts: int, locked_until: datetime) -> bool:
    """Check if PIN is locked"""
    if locked_until and locked_until > datetime.utcnow():
        return True
    return failed_attempts >= 3

def get_pin_lock_time() -> datetime:
    """Get PIN lock expiry time"""
    return datetime.utcnow() + timedelta(minutes=10)

router = APIRouter(prefix="/pin", tags=["PIN Management"])

# ✅ NEW: PIN Reset Endpoints
@router.post("/forgot-pin")
async def forgot_pin(request: ForgotPINRequest, db: Session = Depends(get_db)):
    """Request PIN reset by sending OTP to email"""
    
    user = db.query(User).filter(User.email == request.email).first()
    if not user:
        # Don't reveal that user doesn't exist for security
        return {
            "message": "If the email exists, PIN reset instructions have been sent.",
            "success": True
        }
    
    # Check if user has PIN setup
    try:
        from app.models.pin import UserPIN
        user_pin = db.query(UserPIN).filter(UserPIN.user_id == user.id).first()
        
        if not user_pin or not user_pin.is_active:
            return {
                "message": "If the email exists, PIN reset instructions have been sent.",
                "success": True
            }
    except ImportError:
        # If PIN system not available, still return success for security
        return {
            "message": "If the email exists, PIN reset instructions have been sent.",
            "success": True
        }
    
    # Generate OTP for PIN reset
    otp_code = generate_otp(user.id, OTPPurpose.PIN_RESET, db)
    
    # Send OTP email
    try:
        email_sent = send_otp_email(user.email, otp_code, OTPPurpose.PIN_RESET.value)
        
        if email_sent:
            return {
                "message": "If the email exists, PIN reset instructions have been sent.",
                "success": True
            }
        else:
            # If email fails but OTP was generated, still return success
            return {
                "message": "If the email exists, PIN reset instructions have been sent.",
                "success": True
            }
    except Exception as e:
        # Log error but don't reveal to user
        print(f"PIN reset error for {request.email}: {str(e)}")
        return {
            "message": "If the email exists, PIN reset instructions have been sent.",
            "success": True
        }

@router.post("/reset-pin")
async def reset_pin_with_otp(request: ResetPINRequest, db: Session = Depends(get_db)):
    """Reset PIN using OTP verification"""
    
    user = db.query(User).filter(User.email == request.email).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Validate new PIN
    if not request.new_pin.isdigit() or len(request.new_pin) != 6:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="PIN must be exactly 6 digits"
        )
    
    # Verify OTP for PIN reset
    if not verify_otp(user.id, request.code, OTPPurpose.PIN_RESET, db):
        raise HTTPException(status_code=400, detail="Invalid or expired OTP")
    
    try:
        from app.models.pin import UserPIN
        
        # Update or create PIN
        user_pin = db.query(UserPIN).filter(UserPIN.user_id == user.id).first()
        
        if user_pin:
            # Update existing PIN
            user_pin.pin_hash = get_pin_hash(request.new_pin)
            user_pin.is_active = True
            user_pin.failed_attempts = 0
            user_pin.locked_until = None
            user_pin.updated_at = datetime.utcnow()
        else:
            # Create new PIN (shouldn't happen if user had PIN, but handle anyway)
            new_pin = UserPIN(
                user_id=user.id,
                pin_hash=get_pin_hash(request.new_pin),
                is_active=True,
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow()
            )
            db.add(new_pin)
        
        db.commit()
        
        return {
            "message": "PIN reset successfully. You can now login with your new PIN.",
            "success": True
        }
        
    except ImportError:
        raise HTTPException(status_code=501, detail="PIN system not implemented")
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to reset PIN: {str(e)}"
        )

@router.post("/setup", response_model=PINResponse)
def setup_pin(pin_data: PINCreate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """Setup 6-digit PIN for user"""
    
    # Check if PIN is 6 digits
    if not pin_data.pin.isdigit() or len(pin_data.pin) != 6:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="PIN must be exactly 6 digits"
        )
    
    try:
        # Check if UserPIN model exists
        from app.models.pin import UserPIN
        
        existing_pin = db.query(UserPIN).filter(UserPIN.user_id == current_user.id).first()
        
        if existing_pin:
            # Update existing PIN
            existing_pin.pin_hash = get_pin_hash(pin_data.pin)
            existing_pin.is_active = True
            existing_pin.failed_attempts = 0
            existing_pin.locked_until = None
            existing_pin.updated_at = datetime.utcnow()
        else:
            # Create new PIN
            new_pin = UserPIN(
                user_id=current_user.id,
                pin_hash=get_pin_hash(pin_data.pin),
                is_active=True,
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow()
            )
            db.add(new_pin)
        
        db.commit()
        
        return PINResponse(
            message="PIN setup successfully",
            pin_set=True,
            created_at=datetime.utcnow()
        )
    
    except ImportError:
        # If UserPIN model doesn't exist, create it dynamically
        from sqlalchemy.ext.declarative import declarative_base
        from sqlalchemy import Column, String, Integer, Boolean, DateTime, ForeignKey
        
        Base = declarative_base()
        
        class UserPIN(Base):
            __tablename__ = "user_pins"
            
            id = Column(Integer, primary_key=True, index=True)
            user_id = Column(Integer, ForeignKey("users.id"), unique=True, index=True)
            pin_hash = Column(String(255), nullable=False)
            is_active = Column(Boolean, default=True)
            failed_attempts = Column(Integer, default=0)
            locked_until = Column(DateTime, nullable=True)
            last_used = Column(DateTime, nullable=True)
            created_at = Column(DateTime, default=datetime.utcnow)
            updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
        
        # Create table if it doesn't exist
        Base.metadata.create_all(bind=db.get_bind())
        
        # Now setup the PIN
        existing_pin = db.query(UserPIN).filter(UserPIN.user_id == current_user.id).first()
        
        if existing_pin:
            existing_pin.pin_hash = get_pin_hash(pin_data.pin)
            existing_pin.is_active = True
            existing_pin.failed_attempts = 0
            existing_pin.locked_until = None
            existing_pin.updated_at = datetime.utcnow()
        else:
            new_pin = UserPIN(
                user_id=current_user.id,
                pin_hash=get_pin_hash(pin_data.pin),
                is_active=True
            )
            db.add(new_pin)
        
        db.commit()
        
        return PINResponse(
            message="PIN setup successfully",
            pin_set=True,
            created_at=datetime.utcnow()
        )
    
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to setup PIN: {str(e)}"
        )

@router.post("/verify", response_model=dict)
def verify_pin_login(pin_data: PINVerify, db: Session = Depends(get_db)):
    """Verify PIN for login"""
    
    user = db.query(User).filter(User.email == pin_data.email).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    if not user.is_verified:
        raise HTTPException(status_code=400, detail="Please verify your email first")
    
    try:
        from app.models.pin import UserPIN
        user_pin = db.query(UserPIN).filter(UserPIN.user_id == user.id).first()
        
        if not user_pin or not user_pin.is_active:
            raise HTTPException(status_code=400, detail="PIN not setup for this user")
        
        # Check if PIN is locked
        if is_pin_locked(user_pin.failed_attempts, user_pin.locked_until):
            if not user_pin.locked_until:
                user_pin.locked_until = get_pin_lock_time()
                db.commit()
            
            raise HTTPException(
                status_code=423, 
                detail=f"PIN locked. Try again after {user_pin.locked_until.strftime('%H:%M:%S')}"
            )
        
        # Verify PIN
        if not verify_pin(pin_data.pin, user_pin.pin_hash):
            user_pin.failed_attempts += 1
            
            # Lock PIN after 3 failed attempts
            if user_pin.failed_attempts >= 3:
                user_pin.locked_until = get_pin_lock_time()
            
            user_pin.updated_at = datetime.utcnow()
            db.commit()
            
            remaining_attempts = 3 - user_pin.failed_attempts
            if remaining_attempts > 0:
                raise HTTPException(
                    status_code=401, 
                    detail=f"Invalid PIN. {remaining_attempts} attempts remaining"
                )
            else:
                raise HTTPException(
                    status_code=401,
                    detail="PIN locked due to too many failed attempts. Try again in 10 minutes."
                )
        
        # Reset failed attempts on successful verification
        user_pin.failed_attempts = 0
        user_pin.locked_until = None
        user_pin.last_used = datetime.utcnow()
        user_pin.updated_at = datetime.utcnow()
        db.commit()
        
        # Create and return access token
        token = create_access_token({"sub": user.email})
        
        return {
            "access_token": token,
            "token_type": "bearer",
            "user_id": user.id,
            "email": user.email,
            "message": "PIN verification successful"
        }
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"PIN verification failed: {str(e)}"
        )

@router.get("/status", response_model=PINStatus)
def get_pin_status(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """Get PIN status for current user"""
    
    try:
        from app.models.pin import UserPIN
        user_pin = db.query(UserPIN).filter(UserPIN.user_id == current_user.id).first()
        
        if not user_pin:
            return PINStatus(
                has_pin=False,
                is_active=False,
                failed_attempts=0
            )
        
        # Check if lock has expired
        if user_pin.locked_until and user_pin.locked_until <= datetime.utcnow():
            user_pin.failed_attempts = 0
            user_pin.locked_until = None
            db.commit()
        
        return PINStatus(
            has_pin=True,
            is_active=user_pin.is_active,
            failed_attempts=user_pin.failed_attempts,
            locked_until=user_pin.locked_until,
            last_used=user_pin.last_used
        )
    
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get PIN status: {str(e)}"
        )

@router.post("/disable")
def disable_pin(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """Disable PIN for current user"""
    
    try:
        from app.models.pin import UserPIN
        user_pin = db.query(UserPIN).filter(UserPIN.user_id == current_user.id).first()
        if not user_pin:
            raise HTTPException(status_code=400, detail="PIN not setup for this user")
        
        user_pin.is_active = False
        user_pin.updated_at = datetime.utcnow()
        db.commit()
        
        return {"message": "PIN disabled successfully"}
    
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to disable PIN: {str(e)}"
        )

@router.post("/enable")
def enable_pin(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """Enable PIN for current user"""
    
    try:
        from app.models.pin import UserPIN
        user_pin = db.query(UserPIN).filter(UserPIN.user_id == current_user.id).first()
        if not user_pin:
            raise HTTPException(status_code=400, detail="PIN not setup for this user")
        
        user_pin.is_active = True
        user_pin.failed_attempts = 0
        user_pin.locked_until = None
        user_pin.updated_at = datetime.utcnow()
        db.commit()
        
        return {"message": "PIN enabled successfully"}
    
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to enable PIN: {str(e)}"
        )

@router.delete("/reset")
def reset_pin(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """Reset PIN (requires re-setup)"""
    
    try:
        from app.models.pin import UserPIN
        user_pin = db.query(UserPIN).filter(UserPIN.user_id == current_user.id).first()
        if not user_pin:
            raise HTTPException(status_code=400, detail="PIN not setup for this user")
        
        db.delete(user_pin)
        db.commit()
        
        return {"message": "PIN reset successfully. Please setup a new PIN."}
    
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to reset PIN: {str(e)}"
        )
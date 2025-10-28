# app/core/security.py - UPDATED
from datetime import datetime, timedelta
from typing import Optional
import bcrypt

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import jwt, JWTError
from passlib.context import CryptContext
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db import get_db
from app.models.user import User

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

SECRET_KEY = settings.SECRET_KEY
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = settings.ACCESS_TOKEN_EXPIRE_MINUTES

# ✅ Use HTTPBearer (no client_id/secret UI)
bearer_scheme = HTTPBearer(auto_error=True)


# ---------------- Password utils ---------------- #
def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)


# ---------------- PIN utils ---------------- #
def get_pin_hash(pin: str) -> str:
    """Hash a 6-digit PIN using bcrypt"""
    if len(pin) != 6 or not pin.isdigit():
        raise ValueError("PIN must be exactly 6 digits")
    
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(pin.encode('utf-8'), salt)
    return hashed.decode('utf-8')


def verify_pin(plain_pin: str, hashed_pin: str) -> bool:
    """Verify a PIN against its hash"""
    try:
        if len(plain_pin) != 6 or not plain_pin.isdigit():
            return False
        
        return bcrypt.checkpw(plain_pin.encode('utf-8'), hashed_pin.encode('utf-8'))
    except Exception:
        return False


def is_pin_locked(failed_attempts: int, locked_until: Optional[datetime]) -> bool:
    """Check if PIN is locked based on failed attempts and lock time"""
    if locked_until and locked_until > datetime.utcnow():
        return True
    return failed_attempts >= 3


def get_pin_lock_time() -> datetime:
    """Get PIN lock expiry time (10 minutes from now)"""
    return datetime.utcnow() + timedelta(minutes=10)


# ---------------- JWT utils ---------------- #
def create_access_token(data: dict, expires_delta: Optional[int] = None) -> str:
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(
        minutes=(expires_delta or ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


def decode_access_token(token: str):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except JWTError:
        return None


# ---------------- User dependencies ---------------- #
def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
    db: Session = Depends(get_db)
) -> User:
    """Fetch the actual user record from DB using JWT payload"""
    token = credentials.credentials
    payload = decode_access_token(token)
    
    if payload is None or "sub" not in payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # ✅ Get user by email from the JWT payload
    user_email = payload.get("sub")
    user = db.query(User).filter(User.email == user_email).first()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
        )

    return user  # ✅ Now returns User object, not dict


# ✅ ADD BACK: get_current_user_db function for admin routes
def get_current_user_db(
    db: Session = Depends(get_db),
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
) -> User:
    """Alternative version that might be used by admin routes"""
    return get_current_user(credentials, db)  # Just call the main function


# ✅ ADD: Function to check if user is admin
def get_current_admin_user(
    current_user: User = Depends(get_current_user)
) -> User:
    """Check if current user is an admin"""
    if not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions"
        )
    return current_user
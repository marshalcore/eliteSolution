# app/schemas/user.py
from pydantic import BaseModel, EmailStr
from typing import Optional, Dict, Any
from datetime import datetime

# ------------------------
# Base schemas
# ------------------------
class UserBase(BaseModel):
    email: EmailStr
    first_name: str
    last_name: str
    phone: Optional[str] = None

# ------------------------
# User registration schema
# ------------------------
class UserCreate(UserBase):
    password: str

# ------------------------
# Admin registration schema
# ------------------------
class AdminCreate(UserBase):
    password: str

# ------------------------
# Response schema
# ------------------------
class UserOut(UserBase):
    id: int
    is_verified: bool
    is_active: bool
    is_admin: bool
    kyc_status: str
    kyc_verified_at: Optional[datetime] = None
    created_at: datetime

    class Config:
        from_attributes = True

# ✅ NEW: Enhanced User Response with Additional Fields
class UserProfileResponse(BaseModel):
    id: int
    email: EmailStr
    first_name: str
    last_name: str
    phone: Optional[str] = None
    language_preference: str = "en"  # ✅ NEW
    is_verified: bool
    is_active: bool
    is_admin: bool
    kyc_status: str
    kyc_verified_at: Optional[datetime] = None
    kyc_submitted_at: Optional[datetime] = None
    kyc_rejection_reason: Optional[str] = None
    profile_image: Optional[str] = None
    email_verified: bool = True  # ✅ NEW
    phone_verified: bool = False  # ✅ NEW
    two_factor_enabled: bool = False  # ✅ NEW
    last_password_change: Optional[datetime] = None  # ✅ NEW
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True

# ✅ NEW: User Update Schema
class UserUpdate(BaseModel):
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    phone: Optional[str] = None
    language_preference: Optional[str] = None
    profile_image: Optional[str] = None

# ✅ NEW: Security Settings Schema
class SecuritySettingsUpdate(BaseModel):
    two_factor_enabled: Optional[bool] = None
    security_questions: Optional[Dict[str, Any]] = None

# ✅ NEW: Language Preference Schema
class LanguagePreferenceUpdate(BaseModel):
    language: str
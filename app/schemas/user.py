from pydantic import BaseModel, EmailStr
from typing import Optional
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
    # ⚠️ Do NOT expose is_admin in request body.
    # In API, we'll always enforce is_admin=True automatically.


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

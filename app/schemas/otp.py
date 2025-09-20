# app/schemas/otp.py
from pydantic import BaseModel, EmailStr, Field
from datetime import datetime
from app.models.otp import OTPPurpose


class OTPBase(BaseModel):
    email: EmailStr
    purpose: OTPPurpose


class OTPCreate(OTPBase):
    code: str = Field(..., min_length=6, max_length=6)


class OTPVerify(OTPBase):
    code: str = Field(..., min_length=6, max_length=6)


class OTPOut(OTPBase):
    id: int
    created_at: datetime
    expires_at: datetime
    is_used: bool

    class Config:
        from_attributes = True

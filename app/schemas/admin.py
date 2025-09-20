# app/schemas/admin.py
from pydantic import BaseModel, EmailStr, Field, field_validator
from datetime import datetime


class AdminCreate(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=8, description="Password must be at least 8 characters")
    first_name: str = "Admin"
    last_name: str = "Account"


class AdminLogin(BaseModel):
    email: EmailStr
    password: str


class AdminOut(BaseModel):
    id: int
    email: EmailStr
    is_admin: bool
    is_verified: bool
    created_at: datetime

    class Config:
        from_attributes = True


class KYCUpdate(BaseModel):
    user_id: int
    status: str  # must be "approved" or "rejected"

    @field_validator("status")
    @classmethod
    def validate_status(cls, v: str) -> str:
        allowed = {"approved", "rejected"}
        if v.lower() not in allowed:
            raise ValueError(f"status must be one of {allowed}")
        return v.lower()


# ----------------------------
#  NEW SCHEMAS FOR REGISTRATION VERIFICATION
# ----------------------------
class AdminVerifyRequest(BaseModel):
    email: EmailStr
    code: str = Field(..., min_length=4, max_length=8, description="OTP code sent to email")


class AdminVerifyResponse(BaseModel):
    message: str
    email: EmailStr
    is_verified: bool

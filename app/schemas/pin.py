# app/schemas/pin.py
from pydantic import BaseModel, validator
from typing import Optional
from datetime import datetime

class PINCreate(BaseModel):
    pin: str
    
    @validator('pin')
    def validate_pin_length(cls, v):
        if len(v) != 6 or not v.isdigit():
            raise ValueError('PIN must be exactly 6 digits')
        return v

class PINVerify(BaseModel):
    pin: str
    email: str
    
    @validator('pin')
    def validate_pin_length(cls, v):
        if len(v) != 6 or not v.isdigit():
            raise ValueError('PIN must be exactly 6 digits')
        return v

class PINResponse(BaseModel):
    message: str
    pin_set: bool
    created_at: Optional[datetime] = None

class PINStatus(BaseModel):
    has_pin: bool
    is_active: bool
    failed_attempts: int
    locked_until: Optional[datetime] = None
    last_used: Optional[datetime] = None
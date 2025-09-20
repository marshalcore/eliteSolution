# backend/app/schemas/account.py
from pydantic import BaseModel
from typing import Optional

class AccountCreate(BaseModel):
    currency: Optional[str] = "NGN"
    account_type: Optional[str] = "savings"

class AccountOut(BaseModel):
    id: int
    user_id: int
    account_number: str
    currency: str
    balance_cents: int
    account_type: str

    class Config:
        from_attributes = True   # ✅ Must be indented inside Config

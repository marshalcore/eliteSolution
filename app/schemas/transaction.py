# backend/app/schemas/transaction.py
from pydantic import BaseModel
from typing import Optional
from datetime import datetime

class DepositCreate(BaseModel):
    account_id: int
    amount_cents: int
    method: str
    metadata: Optional[dict] = None

class WithdrawCreate(BaseModel):
    account_id: int
    amount_cents: int
    method: str
    destination: Optional[dict] = None

class TransferCreate(BaseModel):
    from_account_id: int
    to_account_number: str
    to_bank_code: Optional[str] = None
    amount_cents: int
    metadata: Optional[dict] = None

class TransactionOut(BaseModel):
    id: int
    from_account_id: Optional[int]
    to_account_id: Optional[int]
    amount_cents: int
    type: str
    status: str
    reference: Optional[str]
    method: Optional[str]
    metadata: Optional[dict]
    created_at: datetime
    processed_at: Optional[datetime]

    class Config:
        from_attributes = True   # ✅ Must be indented inside Config

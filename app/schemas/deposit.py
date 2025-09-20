from pydantic import BaseModel, Field
from typing import Annotated, Optional
from decimal import Decimal
from datetime import datetime
from enum import Enum


# Provider types
ProviderType = Annotated[str, Field(pattern="^(okx|paystack|flutterwave)$")]

# Currency options
class CurrencyEnum(str, Enum):
    USDT = "USDT"
    BTC = "BTC"
    ETH = "ETH"
    USD = "USD"
    EUR = "EUR"
    GBP = "GBP"
    BNB = "BNB"
    SOL = "SOL"
    ADA = "ADA"
    XRP = "XRP"
    DOGE = "DOGE"


class DepositRequest(BaseModel):
    user_id: int
    amount: Decimal
    provider: ProviderType
    currency: CurrencyEnum  # <-- user must pick

    def normalize_provider(self) -> str:
        return self.provider.strip().lower()


class DepositResponse(BaseModel):
    id: int
    user_id: int
    provider: str
    amount: Decimal
    currency: str
    status: str
    tx_ref: Optional[str]
    created_at: datetime

    class Config:
        orm_mode = True

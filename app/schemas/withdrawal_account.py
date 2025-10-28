# app/schemas/withdrawal_account.py - NEW FILE
from pydantic import BaseModel, validator
from typing import Optional, Dict, Any
from datetime import datetime
from enum import Enum

class AccountType(str, Enum):
    BANK = "bank"
    CRYPTO = "crypto"
    MOBILE_MONEY = "mobile_money"

class Provider(str, Enum):
    PAYSTACK = "paystack"
    FLUTTERWAVE = "flutterwave"
    TRUST_WALLET = "trust_wallet"
    BINANCE = "binance"
    OKX = "okx"
    MANUAL = "manual"

class CryptoNetwork(str, Enum):
    ERC20 = "ERC20"
    BEP20 = "BEP20"
    TRC20 = "TRC20"
    BTC = "BTC"
    LTC = "LTC"

class Cryptocurrency(str, Enum):
    BTC = "BTC"
    ETH = "ETH"
    USDT = "USDT"
    USDC = "USDC"
    BNB = "BNB"
    LTC = "LTC"

class WithdrawalAccountCreate(BaseModel):
    account_type: AccountType
    provider: Provider
    account_name: Optional[str] = None
    account_number: Optional[str] = None
    bank_code: Optional[str] = None
    bank_name: Optional[str] = None
    wallet_address: Optional[str] = None
    wallet_network: Optional[CryptoNetwork] = None
    cryptocurrency: Optional[Cryptocurrency] = None
    phone_number: Optional[str] = None
    mobile_network: Optional[str] = None
    account_metadata: Optional[Dict[str, Any]] = None  # ✅ FIXED: Changed from 'metadata'

    @validator('wallet_address')
    def validate_wallet_address(cls, v, values):
        if values.get('account_type') == AccountType.CRYPTO and not v:
            raise ValueError('Wallet address is required for crypto accounts')
        return v

    @validator('account_number')
    def validate_account_number(cls, v, values):
        if values.get('account_type') == AccountType.BANK and not v:
            raise ValueError('Account number is required for bank accounts')
        return v

    @validator('phone_number')
    def validate_phone_number(cls, v, values):
        if values.get('account_type') == AccountType.MOBILE_MONEY and not v:
            raise ValueError('Phone number is required for mobile money accounts')
        return v

class WithdrawalAccountUpdate(BaseModel):
    account_name: Optional[str] = None
    is_default: Optional[bool] = None
    account_metadata: Optional[Dict[str, Any]] = None  # ✅ FIXED: Changed from 'metadata'

class WithdrawalAccountResponse(BaseModel):
    id: int
    user_id: int
    account_type: AccountType
    provider: Provider
    account_name: Optional[str]
    account_number: Optional[str]
    bank_code: Optional[str]
    bank_name: Optional[str]
    wallet_address: Optional[str]
    wallet_network: Optional[CryptoNetwork]
    cryptocurrency: Optional[Cryptocurrency]
    phone_number: Optional[str]
    mobile_network: Optional[str]
    is_verified: bool
    is_default: bool
    account_metadata: Optional[Dict[str, Any]]  # ✅ FIXED: Added this field
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

class WithdrawalAccountList(BaseModel):
    accounts: list[WithdrawalAccountResponse]
    total: int
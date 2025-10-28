# app/models/withdrawal_account.py - FIXED
from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, Text, JSON
from sqlalchemy.orm import relationship
from app.db.base_class import Base  # ✅ Use consistent Base
from datetime import datetime

class WithdrawalAccount(Base):
    __tablename__ = "withdrawal_accounts"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    
    # Account Type: bank, crypto, mobile_money, etc.
    account_type = Column(String(50), nullable=False)
    
    # Provider: paystack, flutterwave, trust_wallet, binance, etc.
    provider = Column(String(50), nullable=False)
    
    # Account Details (varies by type)
    account_name = Column(String(255))
    account_number = Column(String(255))  # For bank accounts
    bank_code = Column(String(50))  # For bank accounts
    bank_name = Column(String(255))
    
    # Crypto wallet details
    wallet_address = Column(String(255))
    wallet_network = Column(String(50))  # ERC20, BEP20, TRC20, etc.
    cryptocurrency = Column(String(50))  # BTC, ETH, USDT, etc.
    
    # Mobile money details
    phone_number = Column(String(50))
    mobile_network = Column(String(50))
    
    # Verification status
    is_verified = Column(Boolean, default=False)
    is_default = Column(Boolean, default=False)
    
    # Additional metadata
    account_metadata = Column(JSON)  # ✅ FIXED: Consistent with model
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationship
    user = relationship("User", back_populates="withdrawal_accounts")

    def to_dict(self):
        """Convert to dictionary for API response"""
        return {
            "id": self.id,
            "account_type": self.account_type,
            "provider": self.provider,
            "account_name": self.account_name,
            "account_number": self.account_number,
            "bank_code": self.bank_code,
            "bank_name": self.bank_name,
            "wallet_address": self.wallet_address,
            "wallet_network": self.wallet_network,
            "cryptocurrency": self.cryptocurrency,
            "phone_number": self.phone_number,
            "mobile_network": self.mobile_network,
            "is_verified": self.is_verified,
            "is_default": self.is_default,
            "account_metadata": self.account_metadata,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None
        }
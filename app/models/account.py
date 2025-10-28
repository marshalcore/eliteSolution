# app/models/account.py
from sqlalchemy import Column, Integer, String, BigInteger, Boolean, DateTime, ForeignKey, func
from sqlalchemy.orm import relationship
from app.db.base_class import Base

class Account(Base):
    __tablename__ = "accounts"
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    bank_id = Column(Integer, ForeignKey("banks.id", ondelete="SET NULL"), nullable=True)
    account_number = Column(String(64), unique=True, index=True, nullable=False)
    currency = Column(String(3), default="NGN", nullable=False)
    balance_cents = Column(BigInteger, nullable=False, default=0)
    account_type = Column(String(32), default="savings")
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, server_default=func.now())

    user = relationship("User", back_populates="accounts")
    bank = relationship("Bank", back_populates="accounts")
    payments = relationship("Payment", back_populates="account", cascade="all, delete")
    
    # ✅ FIXED: Updated transaction relationships to match Transaction model
    sent_transactions = relationship("Transaction", foreign_keys="Transaction.from_account_id", back_populates="from_account")
    received_transactions = relationship("Transaction", foreign_keys="Transaction.to_account_id", back_populates="to_account")
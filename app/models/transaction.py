# app/models/transaction.py
from sqlalchemy import Column, Integer, String, BigInteger, DateTime, ForeignKey, JSON, func
from sqlalchemy.orm import relationship
from app.db.base_class import Base

class Transaction(Base):
    __tablename__ = "transactions"
    id = Column(Integer, primary_key=True)
    
    # ✅ ADDED: User relationship for the transactions relationship in User model
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    
    from_account_id = Column(Integer, ForeignKey("accounts.id"), nullable=True)
    to_account_id = Column(Integer, ForeignKey("accounts.id"), nullable=True)
    amount_cents = Column(BigInteger, nullable=False)
    type = Column(String(32), nullable=False)
    status = Column(String(32), nullable=False, default="pending")
    reference = Column(String(128), unique=True, index=True, nullable=True)
    method = Column(String(32), nullable=True)
    extra_data = Column(JSON, nullable=True)
    created_at = Column(DateTime, server_default=func.now())
    processed_at = Column(DateTime, nullable=True)
    
    # ✅ Relationships
    user = relationship("User", back_populates="transactions")  # ✅ ADDED: For User.transactions
    from_account = relationship("Account", foreign_keys=[from_account_id], back_populates="sent_transactions")
    to_account = relationship("Account", foreign_keys=[to_account_id], back_populates="received_transactions")
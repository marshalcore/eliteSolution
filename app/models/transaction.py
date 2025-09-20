from sqlalchemy import Column, Integer, String, BigInteger, DateTime, ForeignKey, JSON, func
from sqlalchemy.orm import relationship
from app.db.base_class import Base  # ✅ Consistent import

class Transaction(Base):
    __tablename__ = "transactions"
    id = Column(Integer, primary_key=True)
    from_account_id = Column(Integer, ForeignKey("accounts.id"), nullable=True)
    to_account_id = Column(Integer, ForeignKey("accounts.id"), nullable=True)
    amount_cents = Column(BigInteger, nullable=False)
    type = Column(String(32), nullable=False)
    status = Column(String(32), nullable=False, default="pending")
    reference = Column(String(128), unique=True, index=True, nullable=True)
    method = Column(String(32), nullable=True)
    extra_data = Column(JSON, nullable=True)  # ✅ Changed from String to JSON
    created_at = Column(DateTime, server_default=func.now())
    processed_at = Column(DateTime, nullable=True)
    from_account = relationship("Account", foreign_keys=[from_account_id])
    to_account = relationship("Account", foreign_keys=[to_account_id])
from sqlalchemy import Column, Integer, String, Float, ForeignKey, DateTime, Enum
from sqlalchemy.orm import relationship
from datetime import datetime
import enum
from app.db.base_class import Base  # ✅ Consistent import

class PaymentStatus(str, enum.Enum):
    pending = "pending"
    success = "success"
    failed = "failed"

class Payment(Base):
    __tablename__ = "payments"
    id = Column(Integer, primary_key=True, index=True)
    amount = Column(Float, nullable=False)
    currency = Column(String, default="USD")
    status = Column(String, default="pending")
    method = Column(String, nullable=False)
    reference = Column(String, unique=True, index=True, nullable=False)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"))
    account_id = Column(Integer, ForeignKey("accounts.id", ondelete="CASCADE"))
    created_at = Column(DateTime, default=datetime.utcnow)
    user = relationship("User", back_populates="payments")
    account = relationship("Account", back_populates="payments")
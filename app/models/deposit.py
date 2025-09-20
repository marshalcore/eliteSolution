from sqlalchemy import Column, Integer, String, Numeric, DateTime, ForeignKey, Enum as PgEnum
from sqlalchemy.orm import relationship
from datetime import datetime
from app.db import Base
from app.schemas.deposit import CurrencyEnum


class Deposit(Base):
    __tablename__ = "deposits"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    provider = Column(String, nullable=False)  # okx, paystack, flutterwave
    amount = Column(Numeric(18, 8), nullable=False)  # 8 decimals for crypto
    currency = Column(PgEnum(CurrencyEnum), nullable=False)  # <-- Enum for currencies
    status = Column(String, default="pending")  # pending, success, failed
    tx_ref = Column(String, nullable=True)      # provider transaction ref
    created_at = Column(DateTime, default=datetime.utcnow)

    # Optional relationship
    user = relationship("User", back_populates="deposits")

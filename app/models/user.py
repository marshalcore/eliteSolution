# app/models/user.py

from sqlalchemy import Column, Integer, String, Boolean, DateTime, func
from sqlalchemy.orm import relationship
from app.db.base_class import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    first_name = Column(String, nullable=False)
    last_name = Column(String, nullable=False)
    phone = Column(String, nullable=True, unique=True)
    hashed_password = Column(String, nullable=False)

    # Status flags
    is_active = Column(Boolean, default=True)
    is_verified = Column(Boolean, default=False)  # ✅ OTP verification
    is_admin = Column(Boolean, default=False)     # ✅ Admin role flag

    # KYC fields
    kyc_status = Column(String, default="pending")   # pending | approved | rejected
    kyc_verified_at = Column(DateTime, nullable=True)

    created_at = Column(DateTime, server_default=func.now())

    # Relationships
    accounts = relationship("Account", back_populates="user")
    payments = relationship("Payment", back_populates="user", cascade="all, delete")
    otps = relationship("OTP", back_populates="user", cascade="all, delete-orphan")
    cards = relationship("Card", back_populates="user")

    # ✅ New relationship for deposits
    deposits = relationship("Deposit", back_populates="user", cascade="all, delete-orphan")

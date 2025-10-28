# app/models/user.py - PROPER FIX
from sqlalchemy import Column, Integer, String, Boolean, DateTime, func, Text, JSON
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

    # Language preference field
    language_preference = Column(String, default="en")

    # Status flags
    is_active = Column(Boolean, default=True)
    is_verified = Column(Boolean, default=False)
    is_admin = Column(Boolean, default=False)

    # KYC fields
    kyc_status = Column(String, default="pending")
    kyc_verified_at = Column(DateTime, nullable=True)
    kyc_submitted_at = Column(DateTime, nullable=True)
    kyc_rejection_reason = Column(Text, nullable=True)
    
    # KYC Document fields
    id_document_front = Column(String, nullable=True)
    id_document_back = Column(String, nullable=True)
    proof_of_address = Column(String, nullable=True)
    selfie_photo = Column(String, nullable=True)
    
    # Personal information for KYC
    date_of_birth = Column(DateTime, nullable=True)
    address = Column(Text, nullable=True)
    city = Column(String, nullable=True)
    state = Column(String, nullable=True)
    country = Column(String, nullable=True)
    postal_code = Column(String, nullable=True)
    
    # Profile image field
    profile_image = Column(String, nullable=True)

    # Account management tracking
    email_verified = Column(Boolean, default=True)
    phone_verified = Column(Boolean, default=False)
    last_password_change = Column(DateTime, server_default=func.now())
    
    # Security preferences
    two_factor_enabled = Column(Boolean, default=False)
    security_questions = Column(JSON, nullable=True)

    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    # KEEP ALL YOUR RELATIONSHIPS - DON'T COMMENT ANYTHING OUT
    accounts = relationship("Account", back_populates="user")
    payments = relationship("Payment", back_populates="user", cascade="all, delete")
    otps = relationship("OTP", back_populates="user", cascade="all, delete-orphan")
    cards = relationship("Card", back_populates="user")
    transactions = relationship("Transaction", back_populates="user", cascade="all, delete")
    trading_bots = relationship("TradingBot", back_populates="user", cascade="all, delete")
    withdrawal_accounts = relationship("WithdrawalAccount", back_populates="user")
    pin = relationship("UserPIN", back_populates="user", uselist=False, cascade="all, delete-orphan")

    def to_dict(self):
        """Convert user to dictionary with all fields"""
        return {
            "id": self.id,
            "email": self.email,
            "first_name": self.first_name,
            "last_name": self.last_name,
            "phone": self.phone,
            "language_preference": self.language_preference,
            "is_active": self.is_active,
            "is_verified": self.is_verified,
            "is_admin": self.is_admin,
            "kyc_status": self.kyc_status,
            "profile_image": self.profile_image,
            "email_verified": self.email_verified,
            "phone_verified": self.phone_verified,
            "two_factor_enabled": self.two_factor_enabled,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None
        }
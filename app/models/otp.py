# app/models/otp.py
from sqlalchemy import Column, Integer, String, Boolean, ForeignKey, DateTime, func, Enum
from sqlalchemy.orm import relationship
from app.db.base_class import Base
import datetime
import enum


class OTPPurpose(enum.Enum):
    # User flows - Use lowercase for consistency
    REGISTRATION = "registration"
    LOGIN = "login"
    TRANSFER = "transfer"
    WITHDRAWAL = "withdrawal"
    PASSWORD_RESET = "password_reset"
    KYC_VERIFICATION = "kyc_verification"
    PIN_RESET = "pin_reset"  # ✅ ADDED: For PIN reset functionality

    # Admin flows
    ADMIN_REGISTRATION = "admin_registration"
    ADMIN_LOGIN = "admin_login"


class OTP(Base):
    __tablename__ = "otps"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"))
    code = Column(String(6), nullable=False)
    purpose = Column(Enum(OTPPurpose), nullable=False)
    is_used = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    expires_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.datetime.utcnow() + datetime.timedelta(minutes=10),
    )

    user = relationship("User", back_populates="otps")
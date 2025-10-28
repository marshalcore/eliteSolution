# app/models/__init__.py
from app.db.base_class import Base  # ✅ import Base here

from .user import User
from .account import Account
from .bank import Bank
from .card import Card
from .payment import Payment
from .transaction import Transaction
from .otp import OTP
from .audit_log import AuditLog  
from .deposit import Deposit
from .pin import UserPIN
from .withdrawal_account import WithdrawalAccount  # ✅ ADDED: Import WithdrawalAccount

__all__ = [
    "Base",
    "User",
    "Account",
    "Transaction",
    "Card",
    "Payment",
    "Bank",
    "OTP",
    "AuditLog",  
    "Deposit",
    "UserPIN",
    "WithdrawalAccount",  # ✅ ADDED: Include in exports
]
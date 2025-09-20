# app/db/base_class.py
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()

# Import all models here so Alembic can see them
from app.models.user import User        # noqa: F401
from app.models.account import Account  # noqa: F401
from app.models.payment import Payment  # noqa: F401
from app.models.transaction import Transaction  # noqa: F401
from app.models.card import Card        # noqa: F401
from app.models.bank import Bank        # noqa: F401
from app.models.otp import OTP          # noqa: F401
from app.models.audit_log import AuditLog  # noqa: F401
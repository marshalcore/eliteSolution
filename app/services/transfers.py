# backend/app/services/transfers.py
from sqlalchemy.orm import Session
from app.models.account import Account
from app.models.transaction import Transaction
from app.services.utils import generate_account_number
from datetime import datetime
import uuid

def internal_transfer(db: Session, from_acc: Account, to_acc: Account, amount_cents: int, reference: str | None = None):
    # lock both accounts must already be done by caller
    if from_acc.balance_cents < amount_cents:
        raise ValueError("Insufficient funds")
    from_acc.balance_cents -= amount_cents
    to_acc.balance_cents += amount_cents
    tx = Transaction(
        from_account_id = from_acc.id,
        to_account_id = to_acc.id,
        amount_cents = amount_cents,
        type = "transfer",
        status = "completed",
        reference = reference or str(uuid.uuid4()),
        method = "internal",
        processed_at = datetime.utcnow(),
    )
    db.add(tx)
    db.commit()
    db.refresh(tx)
    return tx

# app/crud/deposit.py
from sqlalchemy.orm import Session
from app.models.deposit import Deposit
from app.schemas.deposit import DepositCreate, DepositUpdate

# Create a deposit record
def create_deposit(db: Session, deposit: DepositCreate):
    db_deposit = Deposit(
        user_id=deposit.user_id,
        amount=deposit.amount,
        currency=deposit.currency,
        provider=deposit.provider,
        status="pending",  # default status
    )
    db.add(db_deposit)
    db.commit()
    db.refresh(db_deposit)
    return db_deposit


# Get deposits for a user
def get_deposits_by_user(db: Session, user_id: int):
    return db.query(Deposit).filter(Deposit.user_id == user_id).all()


# Update deposit status
def update_deposit_status(db: Session, deposit_id: int, status: str):
    db_deposit = db.query(Deposit).filter(Deposit.id == deposit_id).first()
    if db_deposit:
        db_deposit.status = status
        db.commit()
        db.refresh(db_deposit)
    return db_deposit

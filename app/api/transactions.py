# app/api/transactions.py
from fastapi import APIRouter, Depends, HTTPException, Header, BackgroundTasks
from sqlalchemy.orm import Session
from app.db import get_db
from app.schemas.transaction import DepositCreate, WithdrawCreate, TransferCreate, TransactionOut
from app.schemas.otp import OTPVerify
from app.models.account import Account
from app.models.transaction import Transaction
from app.models.otp import OTPPurpose
from app.core.security import decode_access_token
from app.services.otp_service import generate_otp, send_otp_email, verify_otp
from typing import Optional
import uuid
from datetime import datetime

router = APIRouter(prefix="/api/v1/transactions", tags=["transactions"])

def get_current_user_db(authorization: Optional[str] = Header(None), db: Session = Depends(get_db)):
    if not authorization:
        raise HTTPException(status_code=401, detail="Missing authorization")
    token = authorization.split(" ")[1] if " " in authorization else authorization
    payload = decode_access_token(token)
    if not payload:
        raise HTTPException(status_code=401, detail="Invalid token")
    from app.models.user import User
    email = payload.get("sub")
    user = db.query(User).filter(User.email == email).first()
    if not user:
        raise HTTPException(status_code=401, detail="User not found")
    return user

@router.post("/transfer/initiate")
def initiate_transfer(
    transfer_in: TransferCreate,
    authorization: Optional[str] = Header(None),
    db: Session = Depends(get_db)
):
    user = get_current_user_db(authorization, db)
    
    # Check source account
    from_acc = db.query(Account).filter(
        Account.id == transfer_in.from_account_id,
        Account.user_id == user.id
    ).first()
    if not from_acc:
        raise HTTPException(status_code=404, detail="Source account not found")
    
    # Check sufficient balance
    if from_acc.balance_cents < transfer_in.amount_cents:
        raise HTTPException(status_code=400, detail="Insufficient funds")
    
    # Generate OTP for transfer authorization
    otp_code = generate_otp(user.id, OTPPurpose.TRANSFER, db)
    send_otp_email(user.email, otp_code, "transfer")
    
    return {"message": "OTP sent to your email. Please verify to complete transfer."}

@router.post("/transfer/confirm")
def confirm_transfer(
    transfer_in: TransferCreate,
    otp_data: OTPVerify,
    authorization: Optional[str] = Header(None),
    db: Session = Depends(get_db)
):
    user = get_current_user_db(authorization, db)
    
    # Verify OTP
    if not verify_otp(user.id, otp_data.code, OTPPurpose.TRANSFER, db):
        raise HTTPException(status_code=400, detail="Invalid or expired OTP")
    
    # Check source account again
    from_acc = db.query(Account).filter(
        Account.id == transfer_in.from_account_id,
        Account.user_id == user.id
    ).first()
    if not from_acc:
        raise HTTPException(status_code=404, detail="Source account not found")
    
    # Check internal recipient
    to_acc = db.query(Account).filter(Account.account_number == transfer_in.to_account_number).first()
    
    reference = str(uuid.uuid4())
    
    if to_acc:
        # Internal transfer with account locking
        first_id, second_id = (from_acc.id, to_acc.id) if from_acc.id <= to_acc.id else (to_acc.id, from_acc.id)
        a1 = db.query(Account).filter(Account.id == first_id).with_for_update().one()
        a2 = db.query(Account).filter(Account.id == second_id).with_for_update().one()
        real_from = a1 if a1.id == from_acc.id else a2
        real_to = a2 if a2.id == to_acc.id else a1
        
        if real_from.balance_cents < transfer_in.amount_cents:
            raise HTTPException(status_code=400, detail="Insufficient funds")
        
        real_from.balance_cents -= transfer_in.amount_cents
        real_to.balance_cents += transfer_in.amount_cents
        
        txn = Transaction(
            from_account_id=real_from.id,
            to_account_id=real_to.id,
            amount_cents=transfer_in.amount_cents,
            type="transfer",
            status="completed",
            reference=reference,
            method="internal",
            metadata=transfer_in.metadata,
            processed_at=datetime.utcnow()
        )
        db.add(txn)
        db.commit()
        db.refresh(txn)
        return txn
    else:
        # External transfer
        if from_acc.balance_cents < transfer_in.amount_cents:
            raise HTTPException(status_code=400, detail="Insufficient funds")
        
        from_acc.balance_cents -= transfer_in.amount_cents
        
        txn = Transaction(
            from_account_id=from_acc.id,
            amount_cents=transfer_in.amount_cents,
            type="transfer",
            status="pending",
            reference=reference,
            method="external",
            metadata={
                "to_account_number": transfer_in.to_account_number,
                "to_bank_code": transfer_in.to_bank_code
            }
        )
        db.add(txn)
        db.commit()
        db.refresh(txn)
        return txn

@router.post("/withdraw/initiate")
def initiate_withdrawal(
    withdraw_in: WithdrawCreate,
    authorization: Optional[str] = Header(None),
    db: Session = Depends(get_db)
):
    user = get_current_user_db(authorization, db)
    
    account = db.query(Account).filter(
        Account.id == withdraw_in.account_id,
        Account.user_id == user.id
    ).first()
    if not account:
        raise HTTPException(status_code=404, detail="Account not found")
    
    if account.balance_cents < withdraw_in.amount_cents:
        raise HTTPException(status_code=400, detail="Insufficient funds")
    
    # Generate OTP for withdrawal authorization
    otp_code = generate_otp(user.id, OTPPurpose.WITHDRAWAL, db)
    send_otp_email(user.email, otp_code, "withdrawal")
    
    return {"message": "OTP sent to your email. Please verify to complete withdrawal."}

@router.post("/withdraw/confirm")
def confirm_withdrawal(
    withdraw_in: WithdrawCreate,
    otp_data: OTPVerify,
    authorization: Optional[str] = Header(None),
    db: Session = Depends(get_db)
):
    user = get_current_user_db(authorization, db)
    
    # Verify OTP
    if not verify_otp(user.id, otp_data.code, OTPPurpose.WITHDRAWAL, db):
        raise HTTPException(status_code=400, detail="Invalid or expired OTP")
    
    account = db.query(Account).filter(
        Account.id == withdraw_in.account_id,
        Account.user_id == user.id
    ).first()
    if not account:
        raise HTTPException(status_code=404, detail="Account not found")
    
    # Double-check balance with locking
    locked_account = db.query(Account).filter(Account.id == account.id).with_for_update().one()
    if locked_account.balance_cents < withdraw_in.amount_cents:
        raise HTTPException(status_code=400, detail="Insufficient funds")
    
    locked_account.balance_cents -= withdraw_in.amount_cents
    
    reference = str(uuid.uuid4())
    txn = Transaction(
        from_account_id=locked_account.id,
        amount_cents=withdraw_in.amount_cents,
        type="withdrawal",
        status="pending",
        reference=reference,
        method=withdraw_in.method,
        metadata={"destination": withdraw_in.destination}
    )
    db.add(txn)
    db.commit()
    db.refresh(txn)
    
    return txn
# backend/app/api/accounts.py
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.db import get_db
from app.models.user import User
from app.models.account import Account
from app.schemas.account import AccountCreate, AccountOut
from app.core.security import decode_access_token
from fastapi import Header
from typing import Optional

router = APIRouter(prefix="/api/v1/accounts", tags=["accounts"])

# simple dependency to get current_user (JWT from Authorization header)
def get_current_user_db(authorization: Optional[str] = Header(None), db: Session = Depends(get_db)):
    if not authorization:
        raise HTTPException(status_code=401, detail="Missing authorization")
    token = authorization.split(" ")[1] if " " in authorization else authorization
    payload = decode_access_token(token)
    if not payload:
        raise HTTPException(status_code=401, detail="Invalid token")
    email = payload.get("sub")
    user = db.query(User).filter(User.email == email).first()
    if not user:
        raise HTTPException(status_code=401, detail="User not found")
    return user

@router.post("", response_model=AccountOut)
def create_account(account_in: AccountCreate, current_user: User = Depends(get_current_user_db), db: Session = Depends(get_db)):
    from app.services.utils import generate_account_number
    acc_num = generate_account_number()
    acc = Account(user_id=current_user.id, account_number=acc_num, currency=account_in.currency, account_type=account_in.account_type)
    db.add(acc)
    db.commit()
    db.refresh(acc)
    return acc

@router.get("/{account_number}/resolve")
def resolve_account(account_number: str, bank_code: Optional[str] = None, db: Session = Depends(get_db)):
    # internal lookup
    acc = db.query(Account).filter(Account.account_number == account_number).first()
    if acc:
        user = acc.user
        return {"found": True, "name": f"{user.first_name} {user.last_name}", "user_id": user.id}
    # external: you must wire to bank verification API (mock for now)
    # Example mock:
    if bank_code and bank_code != "ELITE_CREDIT":
        return {"found": True, "name": "External Account Holder", "user_id": None}
    return {"found": False}

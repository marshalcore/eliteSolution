# app/api/withdrawal_accounts.py - NEW FILE
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
import re
from datetime import datetime

from app.db.database import get_db
from app.models.user import User
from app.models.withdrawal_account import WithdrawalAccount
from app.schemas.withdrawal_account import (
    WithdrawalAccountCreate, 
    WithdrawalAccountUpdate, 
    WithdrawalAccountResponse,
    WithdrawalAccountList,
    AccountType,
    Provider,
    CryptoNetwork,
    Cryptocurrency
)
from app.core.security import get_current_user

router = APIRouter(prefix="/withdrawal-accounts", tags=["Withdrawal Accounts"])

# Crypto wallet address validation
def validate_crypto_address(address: str, network: CryptoNetwork) -> bool:
    """Validate cryptocurrency wallet addresses"""
    patterns = {
        CryptoNetwork.ERC20: r'^0x[a-fA-F0-9]{40}$',  # Ethereum addresses
        CryptoNetwork.BEP20: r'^0x[a-fA-F0-9]{40}$',  # BSC addresses
        CryptoNetwork.TRC20: r'^T[A-Za-z1-9]{33}$',   # Tron addresses
        CryptoNetwork.BTC: r'^[13][a-km-zA-HJ-NP-Z1-9]{25,34}$|^bc1[a-z0-9]{39,59}$',  # Bitcoin addresses
        CryptoNetwork.LTC: r'^[LM3][a-km-zA-HJ-NP-Z1-9]{26,33}$'  # Litecoin addresses
    }
    
    pattern = patterns.get(network)
    if pattern and re.match(pattern, address):
        return True
    return False

@router.post("/", response_model=WithdrawalAccountResponse)
def create_withdrawal_account(
    account_data: WithdrawalAccountCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Create a new withdrawal account"""
    
    # Validate crypto wallet address if provided
    if account_data.account_type == AccountType.CRYPTO and account_data.wallet_address:
        if not validate_crypto_address(account_data.wallet_address, account_data.wallet_network):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid {account_data.wallet_network} wallet address"
            )
    
    # Check if this is the first account - set as default
    existing_accounts = db.query(WithdrawalAccount).filter(
        WithdrawalAccount.user_id == current_user.id
    ).count()
    
    is_default = existing_accounts == 0
    
    # Create new account
    new_account = WithdrawalAccount(
        user_id=current_user.id,
        account_type=account_data.account_type,
        provider=account_data.provider,
        account_name=account_data.account_name,
        account_number=account_data.account_number,
        bank_code=account_data.bank_code,
        bank_name=account_data.bank_name,
        wallet_address=account_data.wallet_address,
        wallet_network=account_data.wallet_network,
        cryptocurrency=account_data.cryptocurrency,
        phone_number=account_data.phone_number,
        mobile_network=account_data.mobile_network,
        is_verified=False,  # Manual verification required for security
        is_default=is_default,
        account_metadata=account_data.account_metadata or {}  # ✅ FIXED: Changed from 'metadata'
    )
    
    db.add(new_account)
    db.commit()
    db.refresh(new_account)
    
    return new_account

@router.get("/", response_model=WithdrawalAccountList)
def get_withdrawal_accounts(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get all withdrawal accounts for current user"""
    
    accounts = db.query(WithdrawalAccount).filter(
        WithdrawalAccount.user_id == current_user.id
    ).order_by(WithdrawalAccount.is_default.desc(), WithdrawalAccount.created_at.desc()).all()
    
    return WithdrawalAccountList(
        accounts=[account.to_dict() for account in accounts],
        total=len(accounts)
    )

@router.get("/{account_id}", response_model=WithdrawalAccountResponse)
def get_withdrawal_account(
    account_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get specific withdrawal account"""
    
    account = db.query(WithdrawalAccount).filter(
        WithdrawalAccount.id == account_id,
        WithdrawalAccount.user_id == current_user.id
    ).first()
    
    if not account:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Withdrawal account not found"
        )
    
    return account.to_dict()

@router.put("/{account_id}", response_model=WithdrawalAccountResponse)
def update_withdrawal_account(
    account_id: int,
    account_data: WithdrawalAccountUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Update withdrawal account"""
    
    account = db.query(WithdrawalAccount).filter(
        WithdrawalAccount.id == account_id,
        WithdrawalAccount.user_id == current_user.id
    ).first()
    
    if not account:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Withdrawal account not found"
        )
    
    # Update fields
    if account_data.account_name is not None:
        account.account_name = account_data.account_name
    
    if account_data.is_default is not None:
        # If setting as default, remove default from other accounts
        if account_data.is_default:
            db.query(WithdrawalAccount).filter(
                WithdrawalAccount.user_id == current_user.id,
                WithdrawalAccount.is_default == True
            ).update({"is_default": False})
        account.is_default = account_data.is_default
    
    if account_data.account_metadata is not None:  # ✅ FIXED: Changed from 'metadata'
        account.account_metadata = account_data.account_metadata  # ✅ FIXED: Changed from 'metadata'
    
    account.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(account)
    
    return account.to_dict()

@router.delete("/{account_id}")
def delete_withdrawal_account(
    account_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Delete withdrawal account"""
    
    account = db.query(WithdrawalAccount).filter(
        WithdrawalAccount.id == account_id,
        WithdrawalAccount.user_id == current_user.id
    ).first()
    
    if not account:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Withdrawal account not found"
        )
    
    # If deleting default account, set another account as default
    if account.is_default:
        other_account = db.query(WithdrawalAccount).filter(
            WithdrawalAccount.user_id == current_user.id,
            WithdrawalAccount.id != account_id
        ).first()
        
        if other_account:
            other_account.is_default = True
    
    db.delete(account)
    db.commit()
    
    return {"message": "Withdrawal account deleted successfully"}

@router.post("/{account_id}/set-default")
def set_default_account(
    account_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Set an account as default withdrawal account"""
    
    account = db.query(WithdrawalAccount).filter(
        WithdrawalAccount.id == account_id,
        WithdrawalAccount.user_id == current_user.id
    ).first()
    
    if not account:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Withdrawal account not found"
        )
    
    # Remove default from all accounts
    db.query(WithdrawalAccount).filter(
        WithdrawalAccount.user_id == current_user.id
    ).update({"is_default": False})
    
    # Set this account as default
    account.is_default = True
    account.updated_at = datetime.utcnow()
    db.commit()
    
    return {"message": "Default withdrawal account updated successfully"}

@router.get("/supported/providers")
def get_supported_providers():
    """Get list of supported withdrawal providers"""
    return {
        "bank": {
            "paystack": {"supported_countries": ["NG", "GH", "KE", "ZA"]},
            "flutterwave": {"supported_countries": ["NG", "GH", "KE", "UG", "TZ", "ZA"]}
        },
        "crypto": {
            "trust_wallet": {"supported_networks": ["ERC20", "BEP20", "TRC20", "BTC", "LTC"]},
            "binance": {"supported_networks": ["ERC20", "BEP20", "TRC20", "BTC"]},
            "okx": {"supported_networks": ["ERC20", "BEP20", "TRC20", "BTC"]}
        },
        "mobile_money": {
            "paystack": {"supported_countries": ["NG", "GH"]},
            "flutterwave": {"supported_countries": ["NG", "GH", "UG", "TZ", "RW"]}
        }
    }
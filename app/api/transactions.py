# app/api/transactions.py - COMPLETE MERGED VERSION
from fastapi import APIRouter, Depends, HTTPException, Header, BackgroundTasks, WebSocket
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from datetime import datetime
import uuid
import json
import asyncio
import re

from app.db import get_db
from app.schemas.transaction import DepositCreate, WithdrawCreate, TransferCreate, TransactionOut
from app.schemas.otp import OTPVerify
from app.models.account import Account
from app.models.transaction import Transaction
from app.models.user import User
from app.models.withdrawal_account import WithdrawalAccount
from app.models.otp import OTPPurpose
from app.core.security import decode_access_token, get_current_user
from app.services.otp_service import generate_otp, send_otp_email, verify_otp
from app.services.transaction_service import TransactionService, get_transaction_service
from app.services.kyc_service import kyc_service
from app.services.payments import verify_payment_with_routing
from app.services.trust_wallet_service import TrustWalletService
from app.services.payment_router import PaymentRouter

router = APIRouter(prefix="/api/v1/transactions", tags=["transactions"])

# ✅ NEW: Enhanced Withdrawal Request Model
class AdvancedWithdrawCreate(BaseModel):
    amount_cents: int
    account_id: int  # Reference to withdrawal account
    currency: str = "USD"
    notes: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None

# ✅ NEW: Crypto Withdrawal Request
class CryptoWithdrawCreate(BaseModel):
    amount_cents: int
    cryptocurrency: str
    wallet_address: str
    wallet_network: str
    notes: Optional[str] = None

# ✅ NEW: Withdrawal Response Model
class WithdrawalResponse(BaseModel):
    withdrawal_id: str
    status: str
    amount: float
    currency: str
    account_details: Dict[str, Any]
    estimated_completion: Optional[str] = None
    transaction_hash: Optional[str] = None
    fees: Dict[str, float]

# ✅ NEW: WebSocket connection manager
class ConnectionManager:
    def __init__(self):
        self.active_connections: dict = {}

    async def connect(self, websocket: WebSocket, transaction_id: str):
        await websocket.accept()
        self.active_connections[transaction_id] = websocket

    def disconnect(self, transaction_id: str):
        if transaction_id in self.active_connections:
            del self.active_connections[transaction_id]

    async def send_personal_message(self, message: str, transaction_id: str):
        if transaction_id in self.active_connections:
            await self.active_connections[transaction_id].send_text(message)

manager = ConnectionManager()

# ✅ NEW: WebSocket endpoint for real-time transaction updates
@router.websocket("/ws/transaction-status/{tx_id}")
async def transaction_status(websocket: WebSocket, tx_id: str):
    await manager.connect(websocket, tx_id)
    try:
        while True:
            # Send initial status
            await manager.send_personal_message(
                json.dumps({"status": "connected", "transaction_id": tx_id}),
                tx_id
            )
            
            # Simulate status updates
            statuses = ["processing", "verifying", "completed", "failed"]
            for status in statuses:
                await asyncio.sleep(2)
                await manager.send_personal_message(
                    json.dumps({
                        "transaction_id": tx_id,
                        "status": status,
                        "timestamp": datetime.utcnow().isoformat()
                    }),
                    tx_id
                )
                if status == "completed" or status == "failed":
                    break
                    
    except Exception as e:
        print(f"WebSocket error for transaction {tx_id}: {e}")
    finally:
        manager.disconnect(tx_id)

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

def check_kyc_for_transaction(user: User, operation: str = "transaction", amount: float = None):
    """Enhanced KYC check with consistency verification"""
    
    # ✅ CRITICAL FIX: Verify KYC status consistency first
    from app.services.kyc_service import kyc_service
    from app.db.database import SessionLocal
    db_temp = SessionLocal()
    try:
        kyc_service.verify_user_kyc(user.id, db_temp)
        db_temp.refresh(user)
    finally:
        db_temp.close()
    
    # Now check the verified status
    if user.kyc_status != "verified":
        error_messages = {
            "pending": f"KYC verification required. Please complete your KYC verification to perform {operation}.",
            "submitted": f"KYC verification in progress. Your documents are under review. You cannot perform {operation} until verification is complete.",
            "rejected": f"KYC verification rejected. {user.kyc_rejection_reason or 'Please contact support or resubmit your documents.'}"
        }
        
        message = error_messages.get(user.kyc_status, f"KYC verification required for {operation}.")
        
        raise HTTPException(
            status_code=403,
            detail=message
        )
    
    # Check transaction limits based on KYC status
    transaction_limits = {
        "verified": 10000.00,   # $10,000 limit for basic verification
        "enhanced": 50000.00    # $50,000 limit for enhanced verification
    }
    
    if amount:
        user_limit = transaction_limits.get(user.kyc_status, 0)
        if amount > user_limit:
            raise HTTPException(
                status_code=403,
                detail=f"Transaction amount exceeds your limit. Maximum allowed: ${user_limit:,.2f}. Please contact support for higher limits."
            )

# ✅ NEW: HELPER FUNCTIONS
def calculate_withdrawal_fees(amount_cents: int, account_type: str) -> Dict[str, float]:
    """Calculate withdrawal fees based on amount and account type"""
    amount = amount_cents / 100
    
    if account_type == "crypto":
        # Crypto fees: 1% + network fee
        percentage_fee = amount * 0.01
        network_fee = 5.00  # Estimated network fee
        total_fee = percentage_fee + network_fee
    elif account_type == "bank":
        # Bank fees: 1.5% + $2
        percentage_fee = amount * 0.015
        fixed_fee = 2.00
        total_fee = percentage_fee + fixed_fee
    else:  # mobile_money
        # Mobile money: 2% + $1
        percentage_fee = amount * 0.02
        fixed_fee = 1.00
        total_fee = percentage_fee + fixed_fee
    
    return {
        "percentage_fee_cents": int(percentage_fee * 100),
        "fixed_fee_cents": int(fixed_fee * 100),
        "total_fee_cents": int(total_fee * 100),
        "percentage_rate": 1.0 if account_type == "crypto" else (1.5 if account_type == "bank" else 2.0)
    }

def calculate_crypto_fees(amount_cents: int, cryptocurrency: str) -> Dict[str, float]:
    """Calculate cryptocurrency-specific fees"""
    amount = amount_cents / 100
    
    # Different cryptocurrencies have different fee structures
    fee_rates = {
        "BTC": 0.02,  # 2%
        "ETH": 0.015, # 1.5%
        "USDT": 0.01, # 1%
        "USDC": 0.01, # 1%
        "BNB": 0.008  # 0.8%
    }
    
    percentage_rate = fee_rates.get(cryptocurrency, 0.02)  # Default 2%
    percentage_fee = amount * percentage_rate
    network_fee = get_network_fee(cryptocurrency)
    total_fee = percentage_fee + network_fee
    
    return {
        "percentage_fee_cents": int(percentage_fee * 100),
        "network_fee_cents": int(network_fee * 100),
        "total_fee_cents": int(total_fee * 100),
        "percentage_rate": percentage_rate * 100
    }

def get_network_fee(cryptocurrency: str) -> float:
    """Get estimated network fee for cryptocurrency"""
    network_fees = {
        "BTC": 15.00,
        "ETH": 8.00,
        "USDT": 5.00,
        "USDC": 5.00,
        "BNB": 1.00
    }
    return network_fees.get(cryptocurrency, 10.00)

def get_account_display_name(account: WithdrawalAccount) -> Dict[str, Any]:
    """Get display name for withdrawal account"""
    if account.account_type == "crypto":
        return {
            "type": "crypto",
            "display_name": f"{account.cryptocurrency} ({account.wallet_network})",
            "address": f"{account.wallet_address[:10]}...{account.wallet_address[-8:]}",
            "provider": account.provider
        }
    elif account.account_type == "bank":
        return {
            "type": "bank",
            "display_name": f"{account.bank_name} - {account.account_number}",
            "account_name": account.account_name,
            "provider": account.provider
        }
    else:  # mobile_money
        return {
            "type": "mobile_money",
            "display_name": f"{account.mobile_network} - {account.phone_number}",
            "provider": account.provider
        }

def get_estimated_completion(account_type: str) -> str:
    """Get estimated completion time"""
    times = {
        "crypto": "15-30 minutes",
        "bank": "1-3 business days",
        "mobile_money": "Instant - 2 hours"
    }
    return times.get(account_type, "1-3 business days")

def validate_crypto_address(address: str, network: str) -> bool:
    """Validate cryptocurrency wallet address"""
    patterns = {
        "ERC20": r'^0x[a-fA-F0-9]{40}$',
        "BEP20": r'^0x[a-fA-F0-9]{40}$',
        "TRC20": r'^T[A-Za-z1-9]{33}$',
        "BTC": r'^[13][a-km-zA-HJ-NP-Z1-9]{25,34}$|^bc1[a-z0-9]{39,59}$',
        "LTC": r'^[LM3][a-km-zA-HJ-NP-Z1-9]{26,33}$'
    }
    
    pattern = patterns.get(network)
    if pattern and re.match(pattern, address):
        return True
    return False

# ✅ NEW: ADVANCED WITHDRAWAL SYSTEM
@router.post("/withdraw/advanced/initiate", response_model=dict)
def initiate_advanced_withdrawal(
    withdraw_data: AdvancedWithdrawCreate,
    authorization: Optional[str] = Header(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Initiate an advanced withdrawal using pre-saved withdrawal accounts"""
    
    # Check KYC requirement
    amount_dollars = withdraw_data.amount_cents / 100
    check_kyc_for_transaction(current_user, "withdrawal", amount_dollars)
    
    # Get withdrawal account
    withdrawal_account = db.query(WithdrawalAccount).filter(
        WithdrawalAccount.id == withdraw_data.account_id,
        WithdrawalAccount.user_id == current_user.id,
        WithdrawalAccount.is_verified == True
    ).first()
    
    if not withdrawal_account:
        raise HTTPException(status_code=404, detail="Withdrawal account not found or not verified")
    
    # Check user account balance
    user_account = db.query(Account).filter(Account.user_id == current_user.id).first()
    if not user_account:
        raise HTTPException(status_code=404, detail="Account not found")
    
    if user_account.balance_cents < withdraw_data.amount_cents:
        raise HTTPException(status_code=400, detail="Insufficient funds")
    
    # Calculate fees based on account type and amount
    fees = calculate_withdrawal_fees(withdraw_data.amount_cents, withdrawal_account.account_type)
    total_amount = withdraw_data.amount_cents + fees['total_fee_cents']
    
    # Check if user has enough balance including fees
    if user_account.balance_cents < total_amount:
        raise HTTPException(
            status_code=400, 
            detail=f"Insufficient funds. Required: ${total_amount/100:.2f} (including ${fees['total_fee_cents']/100:.2f} fees)"
        )
    
    # Generate OTP for withdrawal authorization
    otp_code = generate_otp(current_user.id, OTPPurpose.WITHDRAWAL, db)
    
    # Enhanced email template
    html_content = f"""
    <html>
      <body style="font-family: Arial, sans-serif; margin:0; padding:0;">
        <table width="100%" bgcolor="#f9f9f9" cellpadding="0" cellspacing="0" style="padding:20px 0;">
          <tr>
            <td align="center">
              <table width="600" cellpadding="0" cellspacing="0" bgcolor="#ffffff" style="border-radius:8px; overflow:hidden;">
                <tr bgcolor="#004080">
                  <td style="padding:20px; text-align:center;">
                    <h2 style="color:white; margin:0;">Withdrawal Authorization</h2>
                  </td>
                </tr>
                <tr>
                  <td style="padding:30px; text-align:center;">
                    <h3 style="color:#333;">Withdrawal Verification</h3>
                    <p style="color:#555;">You are attempting to withdraw:</p>
                    <p style="font-size:24px; font-weight:bold; color:#004080;">${amount_dollars:,.2f}</p>
                    <p style="color:#555;">To: {get_account_display_name(withdrawal_account)['display_name']}</p>
                    <p style="color:#555;">Fees: ${fees['total_fee_cents']/100:.2f}</p>
                    <p style="color:#555;">Total Deducted: ${total_amount/100:.2f}</p>
                    <p style="color:#555;">Use the OTP below to authorize this withdrawal:</p>
                    <p style="font-size:28px; font-weight:bold; color:#004080; letter-spacing:5px;">{otp_code}</p>
                    <p style="color:#777; font-size:12px;">This code will expire in 10 minutes.</p>
                  </td>
                </tr>
                <tr bgcolor="#f1f1f1">
                  <td style="padding:15px; text-align:center; font-size:12px; color:#777;">
                    If you didn't initiate this withdrawal, please contact support immediately.
                  </td>
                </tr>
              </table>
            </td>
          </tr>
        </table>
      </body>
    </html>
    """
    
    send_otp_email(current_user.email, otp_code, "withdrawal", html_content=html_content)
    
    return {
        "message": "OTP sent to your email. Please verify to complete withdrawal.",
        "amount": amount_dollars,
        "fees": fees,
        "total_amount": total_amount / 100,
        "account": get_account_display_name(withdrawal_account),
        "estimated_completion": get_estimated_completion(withdrawal_account.account_type)
    }

@router.post("/withdraw/advanced/confirm", response_model=WithdrawalResponse)
def confirm_advanced_withdrawal(
    withdraw_data: AdvancedWithdrawCreate,
    otp_data: OTPVerify,
    background_tasks: BackgroundTasks,
    authorization: Optional[str] = Header(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Confirm and execute advanced withdrawal"""
    
    # Check KYC requirement again
    amount_dollars = withdraw_data.amount_cents / 100
    check_kyc_for_transaction(current_user, "withdrawal", amount_dollars)
    
    # Verify OTP
    if not verify_otp(current_user.id, otp_data.code, OTPPurpose.WITHDRAWAL, db):
        raise HTTPException(status_code=400, detail="Invalid or expired OTP")
    
    # Get withdrawal account
    withdrawal_account = db.query(WithdrawalAccount).filter(
        WithdrawalAccount.id == withdraw_data.account_id,
        WithdrawalAccount.user_id == current_user.id,
        WithdrawalAccount.is_verified == True
    ).first()
    
    if not withdrawal_account:
        raise HTTPException(status_code=404, detail="Withdrawal account not found")
    
    # Get user account with locking
    user_account = db.query(Account).filter(
        Account.user_id == current_user.id
    ).with_for_update().first()
    
    if not user_account:
        raise HTTPException(status_code=404, detail="Account not found")
    
    # Calculate fees
    fees = calculate_withdrawal_fees(withdraw_data.amount_cents, withdrawal_account.account_type)
    total_amount = withdraw_data.amount_cents + fees['total_fee_cents']
    
    # Double-check balance
    if user_account.balance_cents < total_amount:
        raise HTTPException(status_code=400, detail="Insufficient funds")
    
    # Record balance before transaction
    balance_before = user_account.balance_cents
    
    # Deduct amount and fees
    user_account.balance_cents -= total_amount
    
    # Create withdrawal record
    reference = str(uuid.uuid4())
    withdrawal_txn = Transaction(
        from_account_id=user_account.id,
        amount_cents=withdraw_data.amount_cents,
        type="withdrawal",
        status="processing",  # Will be updated by background task
        reference=reference,
        method=f"{withdrawal_account.provider}_{withdrawal_account.account_type}",
        extra_data={
            "balance_before": balance_before,
            "balance_after": user_account.balance_cents,
            "withdrawal_account_id": withdrawal_account.id,
            "account_type": withdrawal_account.account_type,
            "provider": withdrawal_account.provider,
            "fees": fees,
            "account_details": get_account_display_name(withdrawal_account),
            "notes": withdraw_data.notes,
            **withdraw_data.metadata
        }
    )
    
    db.add(withdrawal_txn)
    db.commit()
    db.refresh(withdrawal_txn)
    
    # Process withdrawal in background
    background_tasks.add_task(
        process_withdrawal_background,
        withdrawal_txn.id,
        withdrawal_account.id,
        current_user.id,
        db
    )
    
    print(f"✅ Advanced withdrawal initiated: ${amount_dollars:.2f} from {current_user.email}")
    
    return WithdrawalResponse(
        withdrawal_id=reference,
        status="processing",
        amount=amount_dollars,
        currency=withdraw_data.currency,
        account_details=get_account_display_name(withdrawal_account),
        estimated_completion=get_estimated_completion(withdrawal_account.account_type),
        fees=fees
    )

# ✅ NEW: CRYPTO WITHDRAWAL ENDPOINT
@router.post("/withdraw/crypto/initiate", response_model=dict)
def initiate_crypto_withdrawal(
    crypto_data: CryptoWithdrawCreate,
    authorization: Optional[str] = Header(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Initiate cryptocurrency withdrawal"""
    
    # Check KYC requirement
    amount_dollars = crypto_data.amount_cents / 100
    check_kyc_for_transaction(current_user, "crypto withdrawal", amount_dollars)
    
    # Validate crypto address
    if not validate_crypto_address(crypto_data.wallet_address, crypto_data.wallet_network):
        raise HTTPException(status_code=400, detail="Invalid cryptocurrency wallet address")
    
    # Check user account balance
    user_account = db.query(Account).filter(Account.user_id == current_user.id).first()
    if not user_account:
        raise HTTPException(status_code=404, detail="Account not found")
    
    if user_account.balance_cents < crypto_data.amount_cents:
        raise HTTPException(status_code=400, detail="Insufficient funds")
    
    # Calculate crypto-specific fees
    fees = calculate_crypto_fees(crypto_data.amount_cents, crypto_data.cryptocurrency)
    total_amount = crypto_data.amount_cents + fees['total_fee_cents']
    
    if user_account.balance_cents < total_amount:
        raise HTTPException(
            status_code=400, 
            detail=f"Insufficient funds. Required: ${total_amount/100:.2f} (including ${fees['total_fee_cents']/100:.2f} fees)"
        )
    
    # Generate OTP
    otp_code = generate_otp(current_user.id, OTPPurpose.WITHDRAWAL, db)
    
    html_content = f"""
    <html>
      <body style="font-family: Arial, sans-serif; margin:0; padding:0;">
        <table width="100%" bgcolor="#f9f9f9" cellpadding="0" cellspacing="0" style="padding:20px 0;">
          <tr>
            <td align="center">
              <table width="600" cellpadding="0" cellspacing="0" bgcolor="#ffffff" style="border-radius:8px; overflow:hidden;">
                <tr bgcolor="#004080">
                  <td style="padding:20px; text-align:center;">
                    <h2 style="color:white; margin:0;">Crypto Withdrawal Authorization</h2>
                  </td>
                </tr>
                <tr>
                  <td style="padding:30px; text-align:center;">
                    <h3 style="color:#333;">Crypto Withdrawal Verification</h3>
                    <p style="color:#555;">You are attempting to withdraw:</p>
                    <p style="font-size:24px; font-weight:bold; color:#004080;">${amount_dollars:,.2f}</p>
                    <p style="color:#555;">Cryptocurrency: {crypto_data.cryptocurrency}</p>
                    <p style="color:#555;">Network: {crypto_data.wallet_network}</p>
                    <p style="color:#555;">Wallet: {crypto_data.wallet_address[:10]}...{crypto_data.wallet_address[-8:]}</p>
                    <p style="color:#555;">Fees: ${fees['total_fee_cents']/100:.2f}</p>
                    <p style="color:#555;">Use the OTP below to authorize:</p>
                    <p style="font-size:28px; font-weight:bold; color:#004080; letter-spacing:5px;">{otp_code}</p>
                  </td>
                </tr>
              </table>
            </td>
          </tr>
        </table>
      </body>
    </html>
    """
    
    send_otp_email(current_user.email, otp_code, "crypto withdrawal", html_content=html_content)
    
    return {
        "message": "OTP sent to your email. Please verify to complete crypto withdrawal.",
        "amount": amount_dollars,
        "cryptocurrency": crypto_data.cryptocurrency,
        "fees": fees,
        "estimated_completion": "15-30 minutes"  # Crypto transactions take time
    }

@router.post("/withdraw/crypto/confirm", response_model=WithdrawalResponse)
def confirm_crypto_withdrawal(
    crypto_data: CryptoWithdrawCreate,
    otp_data: OTPVerify,
    background_tasks: BackgroundTasks,
    authorization: Optional[str] = Header(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Confirm and execute cryptocurrency withdrawal"""
    
    # Check KYC requirement again
    amount_dollars = crypto_data.amount_cents / 100
    check_kyc_for_transaction(current_user, "crypto withdrawal", amount_dollars)
    
    # Verify OTP
    if not verify_otp(current_user.id, otp_data.code, OTPPurpose.WITHDRAWAL, db):
        raise HTTPException(status_code=400, detail="Invalid or expired OTP")
    
    # Validate crypto address again
    if not validate_crypto_address(crypto_data.wallet_address, crypto_data.wallet_network):
        raise HTTPException(status_code=400, detail="Invalid cryptocurrency wallet address")
    
    # Get user account with locking
    user_account = db.query(Account).filter(
        Account.user_id == current_user.id
    ).with_for_update().first()
    
    if not user_account:
        raise HTTPException(status_code=404, detail="Account not found")
    
    # Calculate crypto fees
    fees = calculate_crypto_fees(crypto_data.amount_cents, crypto_data.cryptocurrency)
    total_amount = crypto_data.amount_cents + fees['total_fee_cents']
    
    # Double-check balance
    if user_account.balance_cents < total_amount:
        raise HTTPException(status_code=400, detail="Insufficient funds")
    
    # Record balance before transaction
    balance_before = user_account.balance_cents
    
    # Deduct amount and fees
    user_account.balance_cents -= total_amount
    
    # Create withdrawal record
    reference = str(uuid.uuid4())
    withdrawal_txn = Transaction(
        from_account_id=user_account.id,
        amount_cents=crypto_data.amount_cents,
        type="withdrawal",
        status="processing",
        reference=reference,
        method=f"crypto_{crypto_data.cryptocurrency}",
        extra_data={
            "balance_before": balance_before,
            "balance_after": user_account.balance_cents,
            "cryptocurrency": crypto_data.cryptocurrency,
            "wallet_address": crypto_data.wallet_address,
            "wallet_network": crypto_data.wallet_network,
            "fees": fees,
            "notes": crypto_data.notes
        }
    )
    
    db.add(withdrawal_txn)
    db.commit()
    db.refresh(withdrawal_txn)
    
    # Process crypto withdrawal in background
    background_tasks.add_task(
        process_crypto_withdrawal_background,
        withdrawal_txn.id,
        crypto_data.wallet_address,
        crypto_data.cryptocurrency,
        crypto_data.wallet_network,
        crypto_data.amount_cents,
        db
    )
    
    print(f"✅ Crypto withdrawal initiated: ${amount_dollars:.2f} {crypto_data.cryptocurrency} to {current_user.email}")
    
    return WithdrawalResponse(
        withdrawal_id=reference,
        status="processing",
        amount=amount_dollars,
        currency="USD",
        account_details={
            "type": "crypto",
            "display_name": f"{crypto_data.cryptocurrency} ({crypto_data.wallet_network})",
            "address": f"{crypto_data.wallet_address[:10]}...{crypto_data.wallet_address[-8:]}"
        },
        estimated_completion="15-30 minutes",
        fees=fees
    )

# ✅ NEW: BACKGROUND TASK FOR WITHDRAWAL PROCESSING
async def process_withdrawal_background(transaction_id: int, account_id: int, user_id: int, db: Session):
    """Process withdrawal in background"""
    try:
        # Get transaction and account
        transaction = db.query(Transaction).filter(Transaction.id == transaction_id).first()
        withdrawal_account = db.query(WithdrawalAccount).filter(WithdrawalAccount.id == account_id).first()
        
        if not transaction or not withdrawal_account:
            return
        
        # Update status to processing
        transaction.status = "processing"
        db.commit()
        
        # Simulate processing delay
        await asyncio.sleep(5)
        
        # Process based on account type
        if withdrawal_account.account_type == "crypto":
            await process_crypto_withdrawal(transaction, withdrawal_account, db)
        elif withdrawal_account.account_type == "bank":
            await process_bank_withdrawal(transaction, withdrawal_account, db)
        else:  # mobile_money
            await process_mobile_withdrawal(transaction, withdrawal_account, db)
            
    except Exception as e:
        print(f"Background withdrawal processing error: {e}")
        # Update transaction status to failed
        transaction = db.query(Transaction).filter(Transaction.id == transaction_id).first()
        if transaction:
            transaction.status = "failed"
            transaction.extra_data["error"] = str(e)
            db.commit()

async def process_crypto_withdrawal_background(transaction_id: int, wallet_address: str, cryptocurrency: str, network: str, amount_cents: int, db: Session):
    """Process cryptocurrency withdrawal in background"""
    try:
        transaction = db.query(Transaction).filter(Transaction.id == transaction_id).first()
        if not transaction:
            return
        
        transaction.status = "processing"
        db.commit()
        
        # Use TrustWalletService for crypto withdrawals
        trust_service = TrustWalletService()
        
        # Convert amount to cryptocurrency
        crypto_amount = await convert_to_crypto(
            amount_cents / 100, 
            cryptocurrency
        )
        
        # Create blockchain transaction
        result = await trust_service.create_transaction(
            amount=crypto_amount,
            to_address=wallet_address,
            currency=cryptocurrency
        )
        
        if result["success"]:
            transaction.status = "completed"
            transaction.extra_data["transaction_hash"] = result["transaction_hash"]
            transaction.extra_data["crypto_amount"] = crypto_amount
            transaction.extra_data["blockchain_confirmation"] = True
        else:
            transaction.status = "failed"
            transaction.extra_data["error"] = result.get("error", "Unknown error")
        
        db.commit()
        
    except Exception as e:
        transaction = db.query(Transaction).filter(Transaction.id == transaction_id).first()
        if transaction:
            transaction.status = "failed"
            transaction.extra_data["error"] = str(e)
            db.commit()

async def process_crypto_withdrawal(transaction: Transaction, account: WithdrawalAccount, db: Session):
    """Process cryptocurrency withdrawal"""
    try:
        # Use TrustWalletService for crypto withdrawals
        trust_service = TrustWalletService()
        
        # Convert amount to cryptocurrency
        crypto_amount = await convert_to_crypto(
            transaction.amount_cents / 100, 
            account.cryptocurrency
        )
        
        # Create blockchain transaction
        result = await trust_service.create_transaction(
            amount=crypto_amount,
            to_address=account.wallet_address,
            currency=account.cryptocurrency
        )
        
        if result["success"]:
            transaction.status = "completed"
            transaction.extra_data["transaction_hash"] = result["transaction_hash"]
            transaction.extra_data["crypto_amount"] = crypto_amount
        else:
            transaction.status = "failed"
            transaction.extra_data["error"] = result.get("error", "Unknown error")
        
        db.commit()
        
    except Exception as e:
        transaction.status = "failed"
        transaction.extra_data["error"] = str(e)
        db.commit()

async def process_bank_withdrawal(transaction: Transaction, account: WithdrawalAccount, db: Session):
    """Process bank withdrawal"""
    try:
        # Simulate bank transfer processing
        await asyncio.sleep(10)  # Simulate bank processing time
        
        # In production, integrate with Paystack/Flutterwave bank transfer API
        transaction.status = "completed"
        transaction.extra_data["bank_reference"] = f"BANK_{uuid.uuid4().hex[:10].upper()}"
        db.commit()
        
    except Exception as e:
        transaction.status = "failed"
        transaction.extra_data["error"] = str(e)
        db.commit()

async def process_mobile_withdrawal(transaction: Transaction, account: WithdrawalAccount, db: Session):
    """Process mobile money withdrawal"""
    try:
        # Simulate mobile money processing
        await asyncio.sleep(3)  # Simulate mobile money processing
        
        transaction.status = "completed"
        transaction.extra_data["mobile_reference"] = f"MOBILE_{uuid.uuid4().hex[:8].upper()}"
        db.commit()
        
    except Exception as e:
        transaction.status = "failed"
        transaction.extra_data["error"] = str(e)
        db.commit()

async def convert_to_crypto(amount_usd: float, cryptocurrency: str) -> float:
    """Convert USD amount to cryptocurrency"""
    # Mock conversion rates - in production, use real-time rates
    rates = {
        "BTC": 0.000025,  # ~$40,000 per BTC
        "ETH": 0.0004,    # ~$2,500 per ETH
        "USDT": 1.0,      # 1:1 for stablecoins
        "USDC": 1.0,
        "BNB": 0.003      # ~$300 per BNB
    }
    rate = rates.get(cryptocurrency, 1.0)
    return amount_usd * rate

# ✅ KEEP ALL YOUR EXISTING ENDPOINTS (they're working fine)
@router.post("/transfer/initiate")
def initiate_transfer(
    transfer_in: TransferCreate,
    authorization: Optional[str] = Header(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Initiate a transfer with KYC verification"""
    
    # Check KYC requirement
    amount_dollars = transfer_in.amount_cents / 100
    check_kyc_for_transaction(current_user, "transfer", amount_dollars)
    
    # Check source account
    from_acc = db.query(Account).filter(
        Account.id == transfer_in.from_account_id,
        Account.user_id == current_user.id
    ).first()
    if not from_acc:
        raise HTTPException(status_code=404, detail="Source account not found")
    
    # Check sufficient balance
    if from_acc.balance_cents < transfer_in.amount_cents:
        raise HTTPException(status_code=400, detail="Insufficient funds")
    
    # Check if transferring to own account
    if transfer_in.to_account_number:
        to_acc = db.query(Account).filter(Account.account_number == transfer_in.to_account_number).first()
        if to_acc and to_acc.user_id == current_user.id:
            raise HTTPException(status_code=400, detail="Cannot transfer to your own account")
    
    # Generate OTP for transfer authorization
    otp_code = generate_otp(current_user.id, OTPPurpose.TRANSFER, db)
    
    # Enhanced email template for transfer OTP
    html_content = f"""
    <html>
      <body style="font-family: Arial, sans-serif; margin:0; padding:0;">
        <table width="100%" bgcolor="#f9f9f9" cellpadding="0" cellspacing="0" style="padding:20px 0;">
          <tr>
            <td align="center">
              <table width="600" cellpadding="0" cellspacing="0" bgcolor="#ffffff" style="border-radius:8px; overflow:hidden;">
                <tr bgcolor="#004080">
                  <td style="padding:20px; text-align:center;">
                    <h2 style="color:white; margin:0;">Transfer Authorization</h2>
                  </td>
                </tr>
                <tr>
                  <td style="padding:30px; text-align:center;">
                    <h3 style="color:#333;">Transfer Verification</h3>
                    <p style="color:#555;">You are attempting to transfer:</p>
                    <p style="font-size:24px; font-weight:bold; color:#004080;">${amount_dollars:,.2f}</p>
                    <p style="color:#555;">To account: {transfer_in.to_account_number or 'External Account'}</p>
                    <p style="color:#555;">Use the OTP below to authorize this transfer:</p>
                    <p style="font-size:28px; font-weight:bold; color:#004080; letter-spacing:5px;">{otp_code}</p>
                    <p style="color:#777; font-size:12px;">This code will expire in 10 minutes.</p>
                  </td>
                </tr>
                <tr bgcolor="#f1f1f1">
                  <td style="padding:15px; text-align:center; font-size:12px; color:#777;">
                    If you didn't initiate this transfer, please contact support immediately.
                  </td>
                </tr>
              </table>
            </td>
          </tr>
        </table>
      </body>
    </html>
    """
    
    send_otp_email(current_user.email, otp_code, "transfer", html_content=html_content)
    
    return {
        "message": "OTP sent to your email. Please verify to complete transfer.",
        "amount": amount_dollars,
        "currency": "USD",
        "recipient": transfer_in.to_account_number or "External Account"
    }

@router.post("/transfer/confirm")
def confirm_transfer(
    transfer_in: TransferCreate,
    otp_data: OTPVerify,
    authorization: Optional[str] = Header(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Confirm and execute a transfer with KYC verification"""
    
    # Check KYC requirement again for security
    amount_dollars = transfer_in.amount_cents / 100
    check_kyc_for_transaction(current_user, "transfer", amount_dollars)
    
    # Verify OTP
    if not verify_otp(current_user.id, otp_data.code, OTPPurpose.TRANSFER, db):
        raise HTTPException(status_code=400, detail="Invalid or expired OTP")
    
    # Check source account again
    from_acc = db.query(Account).filter(
        Account.id == transfer_in.from_account_id,
        Account.user_id == current_user.id
    ).first()
    if not from_acc:
        raise HTTPException(status_code=404, detail="Source account not found")
    
    # Check internal recipient
    to_acc = db.query(Account).filter(Account.account_number == transfer_in.to_account_number).first()
    
    reference = str(uuid.uuid4())
    
    if to_acc:
        # Internal transfer with account locking and KYC check for recipient
        if to_acc.user_id != current_user.id:
            recipient_user = db.query(User).filter(User.id == to_acc.user_id).first()
            if recipient_user and recipient_user.kyc_status != "verified":
                raise HTTPException(
                    status_code=400, 
                    detail="Recipient account is not KYC verified. Transfers can only be made to verified accounts."
                )
        
        # Internal transfer with account locking
        first_id, second_id = (from_acc.id, to_acc.id) if from_acc.id <= to_acc.id else (to_acc.id, from_acc.id)
        a1 = db.query(Account).filter(Account.id == first_id).with_for_update().one()
        a2 = db.query(Account).filter(Account.id == second_id).with_for_update().one()
        real_from = a1 if a1.id == from_acc.id else a2
        real_to = a2 if a2.id == to_acc.id else a1
        
        if real_from.balance_cents < transfer_in.amount_cents:
            raise HTTPException(status_code=400, detail="Insufficient funds")
        
        # Record balances before transaction
        from_balance_before = real_from.balance_cents
        to_balance_before = real_to.balance_cents if real_to else 0
        
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
            extra_data={
                "from_balance_before": from_balance_before,
                "to_balance_before": to_balance_before,
                "from_balance_after": real_from.balance_cents,
                "to_balance_after": real_to.balance_cents,
                "description": f"Transfer to {transfer_in.to_account_number}",
                **transfer_in.extra_data
            } if transfer_in.extra_data else {
                "from_balance_before": from_balance_before,
                "to_balance_before": to_balance_before,
                "from_balance_after": real_from.balance_cents,
                "to_balance_after": real_to.balance_cents,
                "description": f"Transfer to {transfer_in.to_account_number}"
            },
            processed_at=datetime.utcnow()
        )
        db.add(txn)
        db.commit()
        db.refresh(txn)
        
        print(f"✅ Internal transfer completed: ${amount_dollars:.2f} from {current_user.email}")
        
        return {
            "message": "Transfer completed successfully",
            "transaction_id": txn.reference,
            "amount": amount_dollars,
            "recipient": transfer_in.to_account_number,
            "new_balance": real_from.balance_cents / 100
        }
    else:
        # External transfer
        if from_acc.balance_cents < transfer_in.amount_cents:
            raise HTTPException(status_code=400, detail="Insufficient funds")
        
        # Record balance before transaction
        balance_before = from_acc.balance_cents
        from_acc.balance_cents -= transfer_in.amount_cents
        
        txn = Transaction(
            from_account_id=from_acc.id,
            amount_cents=transfer_in.amount_cents,
            type="transfer",
            status="pending",
            reference=reference,
            method="external",
            extra_data={
                "balance_before": balance_before,
                "balance_after": from_acc.balance_cents,
                "to_account_number": transfer_in.to_account_number,
                "to_bank_code": transfer_in.to_bank_code,
                "description": f"External transfer to {transfer_in.to_account_number}",
                **transfer_in.extra_data
            } if transfer_in.extra_data else {
                "balance_before": balance_before,
                "balance_after": from_acc.balance_cents,
                "to_account_number": transfer_in.to_account_number,
                "to_bank_code": transfer_in.to_bank_code,
                "description": f"External transfer to {transfer_in.to_account_number}"
            }
        )
        db.add(txn)
        db.commit()
        db.refresh(txn)
        
        print(f"✅ External transfer initiated: ${amount_dollars:.2f} from {current_user.email}")
        
        return {
            "message": "External transfer initiated successfully",
            "transaction_id": txn.reference,
            "amount": amount_dollars,
            "recipient": transfer_in.to_account_number,
            "status": "pending",
            "new_balance": from_acc.balance_cents / 100
        }

@router.post("/withdraw/initiate")
def initiate_withdrawal(
    withdraw_in: WithdrawCreate,
    authorization: Optional[str] = Header(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Initiate a withdrawal with KYC verification"""
    
    # Check KYC requirement
    amount_dollars = withdraw_in.amount_cents / 100
    check_kyc_for_transaction(current_user, "withdrawal", amount_dollars)
    
    account = db.query(Account).filter(
        Account.id == withdraw_in.account_id,
        Account.user_id == current_user.id
    ).first()
    if not account:
        raise HTTPException(status_code=404, detail="Account not found")
    
    if account.balance_cents < withdraw_in.amount_cents:
        raise HTTPException(status_code=400, detail="Insufficient funds")
    
    # Generate OTP for withdrawal authorization
    otp_code = generate_otp(current_user.id, OTPPurpose.WITHDRAWAL, db)
    
    # Enhanced email template for withdrawal OTP
    html_content = f"""
    <html>
      <body style="font-family: Arial, sans-serif; margin:0; padding:0;">
        <table width="100%" bgcolor="#f9f9f9" cellpadding="0" cellspacing="0" style="padding:20px 0;">
          <tr>
            <td align="center">
              <table width="600" cellpadding="0" cellspacing="0" bgcolor="#ffffff" style="border-radius:8px; overflow:hidden;">
                <tr bgcolor="#004080">
                  <td style="padding:20px; text-align:center;">
                    <h2 style="color:white; margin:0;">Withdrawal Authorization</h2>
                  </td>
                </tr>
                <tr>
                  <td style="padding:30px; text-align:center;">
                    <h3 style="color:#333;">Withdrawal Verification</h3>
                    <p style="color:#555;">You are attempting to withdraw:</p>
                    <p style="font-size:24px; font-weight:bold; color:#004080;">${amount_dollars:,.2f}</p>
                    <p style="color:#555;">Method: {withdraw_in.method or 'Standard Withdrawal'}</p>
                    <p style="color:#555;">Use the OTP below to authorize this withdrawal:</p>
                    <p style="font-size:28px; font-weight:bold; color:#004080; letter-spacing:5px;">{otp_code}</p>
                    <p style="color:#777; font-size:12px;">This code will expire in 10 minutes.</p>
                  </td>
                </tr>
                <tr bgcolor="#f1f1f1">
                  <td style="padding:15px; text-align:center; font-size:12px; color:#777;">
                    If you didn't initiate this withdrawal, please contact support immediately.
                  </td>
                </tr>
              </table>
            </td>
          </tr>
        </table>
      </body>
    </html>
    """
    
    send_otp_email(current_user.email, otp_code, "withdrawal", html_content=html_content)
    
    return {
        "message": "OTP sent to your email. Please verify to complete withdrawal.",
        "amount": amount_dollars,
        "currency": "USD",
        "method": withdraw_in.method
    }

@router.post("/withdraw/confirm")
def confirm_withdrawal(
    withdraw_in: WithdrawCreate,
    otp_data: OTPVerify,
    authorization: Optional[str] = Header(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Confirm and execute a withdrawal with KYC verification"""
    
    # Check KYC requirement again for security
    amount_dollars = withdraw_in.amount_cents / 100
    check_kyc_for_transaction(current_user, "withdrawal", amount_dollars)
    
    # Verify OTP
    if not verify_otp(current_user.id, otp_data.code, OTPPurpose.WITHDRAWAL, db):
        raise HTTPException(status_code=400, detail="Invalid or expired OTP")
    
    account = db.query(Account).filter(
        Account.id == withdraw_in.account_id,
        Account.user_id == current_user.id
    ).first()
    if not account:
        raise HTTPException(status_code=404, detail="Account not found")
    
    # Double-check balance with locking
    locked_account = db.query(Account).filter(Account.id == account.id).with_for_update().one()
    if locked_account.balance_cents < withdraw_in.amount_cents:
        raise HTTPException(status_code=400, detail="Insufficient funds")
    
    # Record balance before transaction
    balance_before = locked_account.balance_cents
    locked_account.balance_cents -= withdraw_in.amount_cents
    
    reference = str(uuid.uuid4())
    txn = Transaction(
        from_account_id=locked_account.id,
        amount_cents=withdraw_in.amount_cents,
        type="withdrawal",
        status="completed",
        reference=reference,
        method=withdraw_in.method,
        extra_data={
            "balance_before": balance_before,
            "balance_after": locked_account.balance_cents,
            "destination": withdraw_in.destination,
            "description": f"Withdrawal via {withdraw_in.method}"
        }
    )
    db.add(txn)
    db.commit()
    db.refresh(txn)
    
    print(f"✅ Withdrawal completed: ${amount_dollars:.2f} from {current_user.email}")
    
    return {
        "message": "Withdrawal completed successfully",
        "transaction_id": txn.reference,
        "amount": amount_dollars,
        "method": withdraw_in.method,
        "new_balance": locked_account.balance_cents / 100
    }

@router.post("/deposit")
def create_deposit(
    deposit_in: DepositCreate,
    authorization: Optional[str] = Header(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Create a deposit with KYC verification"""
    
    # Check KYC requirement for deposits over certain amount
    amount_dollars = deposit_in.amount_cents / 100
    if amount_dollars > 5000:  # Large deposit threshold
        check_kyc_for_transaction(current_user, "large deposit", amount_dollars)
    
    account = db.query(Account).filter(
        Account.id == deposit_in.account_id,
        Account.user_id == current_user.id
    ).first()
    if not account:
        raise HTTPException(status_code=404, detail="Account not found")
    
    # Record balance before transaction
    balance_before = account.balance_cents
    account.balance_cents += deposit_in.amount_cents
    
    reference = str(uuid.uuid4())
    txn = Transaction(
        to_account_id=account.id,
        amount_cents=deposit_in.amount_cents,
        type="deposit",
        status="completed",
        reference=reference,
        method=deposit_in.method,
        extra_data={
            "balance_before": balance_before,
            "balance_after": account.balance_cents,
            "description": f"Deposit via {deposit_in.method}",
            **deposit_in.extra_data
        } if deposit_in.extra_data else {
            "balance_before": balance_before,
            "balance_after": account.balance_cents,
            "description": f"Deposit via {deposit_in.method}"
        },
        processed_at=datetime.utcnow()
    )
    db.add(txn)
    db.commit()
    db.refresh(txn)
    
    print(f"✅ Deposit completed: ${amount_dollars:.2f} to {current_user.email}")
    
    return {
        "message": "Deposit completed successfully",
        "transaction_id": txn.reference,
        "amount": amount_dollars,
        "method": deposit_in.method,
        "new_balance": account.balance_cents / 100
    }

@router.get("/history")
def get_transaction_history(
    authorization: Optional[str] = Header(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    limit: int = 50,
    offset: int = 0
):
    """Get user's transaction history"""
    
    # Get user's accounts
    accounts = db.query(Account).filter(Account.user_id == current_user.id).all()
    account_ids = [acc.id for acc in accounts]
    
    # Query transactions where user is either sender or receiver
    transactions = db.query(Transaction).filter(
        (Transaction.from_account_id.in_(account_ids)) | 
        (Transaction.to_account_id.in_(account_ids))
    ).order_by(Transaction.created_at.desc()).offset(offset).limit(limit).all()
    
    # Format response
    formatted_transactions = []
    for txn in transactions:
        is_debit = txn.from_account_id in account_ids
        formatted_transactions.append({
            "id": txn.id,
            "transaction_id": txn.reference,
            "date": txn.created_at.isoformat(),
            "amount": (txn.amount_cents / 100) * (-1 if is_debit else 1),
            "currency": "USD",
            "description": txn.extra_data.get("description", f"{txn.type.title()}") if txn.extra_data else f"{txn.type.title()}",
            "type": "debit" if is_debit else "credit",
            "status": txn.status,
            "method": txn.method
        })
    
    return {
        "transactions": formatted_transactions,
        "total_count": len(formatted_transactions),
        "kyc_status": current_user.kyc_status,
        "can_transact": current_user.kyc_status == "verified"
    }

@router.get("/account-summary")
def get_account_summary(
    authorization: Optional[str] = Header(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get comprehensive account summary with KYC status"""
    
    accounts = db.query(Account).filter(Account.user_id == current_user.id).all()
    
    account_summaries = []
    total_balance = 0
    
    for account in accounts:
        account_summaries.append({
            "account_number": account.account_number,
            "balance": account.balance_cents / 100,
            "currency": account.currency,
            "account_type": account.account_type,
            "is_active": account.is_active
        })
        total_balance += account.balance_cents / 100
    
    transaction_limits = {
        "pending": 0,
        "submitted": 0,
        "rejected": 0,
        "verified": 10000.00,
        "enhanced": 50000.00
    }
    
    return {
        "user": {
            "name": f"{current_user.first_name} {current_user.last_name}",
            "email": current_user.email,
            "kyc_status": current_user.kyc_status,
            "kyc_verified_at": current_user.kyc_verified_at.isoformat() if current_user.kyc_verified_at else None
        },
        "accounts": account_summaries,
        "total_balance": total_balance,
        "can_transact": current_user.kyc_status == "verified",
        "transaction_limit": transaction_limits.get(current_user.kyc_status, 0),
        "currency": "USD"
    }
# app/services/transaction_service.py
from fastapi import HTTPException, Depends
from sqlalchemy.orm import Session
from datetime import datetime
from typing import Optional, Dict, Any
import uuid

from app.models.user import User
from app.models.account import Account
from app.models.transaction import Transaction
from app.db import get_db

class TransactionService:
    def __init__(self, db: Session):
        self.db = db
        self.transaction_limits = {
            "pending": 0,           # No transactions allowed
            "submitted": 0,         # No transactions allowed
            "rejected": 0,          # No transactions allowed
            "verified": 10000.00,   # $10,000 limit for basic verification
            "enhanced": 50000.00    # $50,000 limit for enhanced verification
        }

    def check_kyc_requirement(self, user: User, amount: float = None) -> bool:
        """Check if user can perform transaction based on KYC status and amount"""
        
        if user.kyc_status != "verified":
            error_messages = {
                "pending": "KYC verification required. Please complete your KYC verification to perform transactions.",
                "submitted": "KYC verification in progress. Your documents are under review. You cannot perform transactions until verification is complete.",
                "rejected": f"KYC verification rejected. {user.kyc_rejection_reason or 'Please contact support or resubmit your documents.'}"
            }
            
            raise HTTPException(
                status_code=403,
                detail=error_messages.get(user.kyc_status, "KYC verification required.")
            )
        
        # Check transaction limits based on verification level
        if amount:
            user_limit = self.transaction_limits.get(user.kyc_status, 0)
            if amount > user_limit:
                raise HTTPException(
                    status_code=403,
                    detail=f"Transaction amount exceeds your limit. Maximum allowed: ${user_limit:,.2f}. Please contact support for higher limits."
                )
        
        return True

    def validate_transaction(self, user: User, amount: float, transaction_type: str) -> Dict[str, Any]:
        """Validate transaction before processing"""
        
        # Check KYC requirements
        self.check_kyc_requirement(user, amount)
        
        # Get user's account
        account = self.db.query(Account).filter(Account.user_id == user.id).first()
        if not account:
            raise HTTPException(status_code=404, detail="Account not found")
        
        # Check if account is active
        if not account.is_active:
            raise HTTPException(status_code=400, detail="Account is inactive")
        
        # Validate amount
        if amount <= 0:
            raise HTTPException(status_code=400, detail="Amount must be greater than zero")
        
        # Check for sufficient funds for debit transactions
        if transaction_type == "debit" and account.balance_cents < (amount * 100):
            raise HTTPException(
                status_code=400, 
                detail=f"Insufficient funds. Available balance: ${account.balance_cents / 100:.2f}"
            )
        
        # Check for suspiciously large transactions
        if amount > 5000:  # Flag transactions over $5,000 for review
            print(f"⚠️  Large transaction detected: ${amount:.2f} for user {user.email}")
        
        return {
            "account": account,
            "is_valid": True
        }

    def process_transaction(self, user: User, amount: float, transaction_type: str, 
                          description: str, recipient_account: str = None) -> Dict[str, Any]:
        """Process transaction with comprehensive KYC and validation checks"""
        
        try:
            # Validate transaction
            validation_result = self.validate_transaction(user, amount, transaction_type)
            account = validation_result["account"]
            
            # Generate unique transaction ID
            transaction_id = f"txn_{user.id}_{uuid.uuid4().hex[:8]}_{int(datetime.now().timestamp())}"
            
            # Calculate new balance
            amount_cents = int(amount * 100)
            if transaction_type == "debit":
                new_balance_cents = account.balance_cents - amount_cents
            else:  # credit
                new_balance_cents = account.balance_cents + amount_cents
            
            # Update account balance
            old_balance_cents = account.balance_cents
            account.balance_cents = new_balance_cents
            
            # ✅ UPDATED: Create transaction record with user_id
            transaction = Transaction(
                user_id=user.id,  # ✅ ADDED: user_id for direct relationship
                from_account_id=account.id if transaction_type == "debit" else None,
                to_account_id=account.id if transaction_type == "credit" else None,
                amount_cents=amount_cents,
                type=transaction_type,
                status="completed",
                reference=transaction_id,
                method="internal",
                extra_data={
                    "description": description,
                    "recipient_account": recipient_account,
                    "balance_before": old_balance_cents,
                    "balance_after": new_balance_cents,
                },
                processed_at=datetime.utcnow()
            )
            self.db.add(transaction)
            self.db.commit()
            
            print(f"✅ Transaction processed: {transaction_type} ${amount:.2f} for user {user.email}")
            
            return {
                "success": True,
                "transaction_id": transaction_id,
                "transaction_type": transaction_type,
                "amount": amount,
                "description": description,
                "old_balance": old_balance_cents / 100,
                "new_balance": new_balance_cents / 100,
                "currency": account.currency,
                "timestamp": datetime.now().isoformat()
            }
            
        except HTTPException:
            raise
        except Exception as e:
            self.db.rollback()
            print(f"❌ Error processing transaction: {e}")
            raise HTTPException(status_code=500, detail="Failed to process transaction")

    def get_transaction_history(self, user: User, limit: int = 50, offset: int = 0) -> Dict[str, Any]:
        """Get user's transaction history - NOW USING DIRECT USER RELATIONSHIP"""
        
        try:
            # ✅ UPDATED: Now we can query directly by user_id for better performance
            transactions = self.db.query(Transaction).filter(
                Transaction.user_id == user.id
            ).order_by(Transaction.created_at.desc()).offset(offset).limit(limit).all()
            
            # Get user's account for balance info
            account = self.db.query(Account).filter(Account.user_id == user.id).first()
            if not account:
                raise HTTPException(status_code=404, detail="Account not found")
            
            # Format response
            formatted_transactions = []
            for txn in transactions:
                # Determine if transaction is debit or credit for this user
                is_debit = txn.from_account_id == account.id if txn.from_account_id else False
                
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
                "current_balance": account.balance_cents / 100,
                "currency": account.currency
            }
            
        except Exception as e:
            print(f"❌ Error fetching transaction history: {e}")
            raise HTTPException(status_code=500, detail="Failed to fetch transaction history")

    def get_account_summary(self, user: User) -> Dict[str, Any]:
        """Get comprehensive account summary with KYC status"""
        
        try:
            account = self.db.query(Account).filter(Account.user_id == user.id).first()
            if not account:
                raise HTTPException(status_code=404, detail="Account not found")
            
            return {
                "account_number": account.account_number,
                "balance": account.balance_cents / 100,
                "currency": account.currency,
                "account_type": account.account_type,
                "is_active": account.is_active,
                "kyc_status": user.kyc_status,
                "can_transact": user.kyc_status == "verified",
                "transaction_limit": self.transaction_limits.get(user.kyc_status, 0),
                "member_since": user.created_at.isoformat() if user.created_at else None
            }
            
        except Exception as e:
            print(f"❌ Error fetching account summary: {e}")
            raise HTTPException(status_code=500, detail="Failed to fetch account summary")

    def transfer_funds(self, user: User, amount: float, recipient_account: str, 
                      description: str = "Funds transfer") -> Dict[str, Any]:
        """Transfer funds to another account"""
        
        try:
            # Validate recipient account exists
            recipient_acc = self.db.query(Account).filter(
                Account.account_number == recipient_account
            ).first()
            
            if not recipient_acc:
                raise HTTPException(status_code=404, detail="Recipient account not found")
            
            # Get sender's account
            sender_account = self.db.query(Account).filter(Account.user_id == user.id).first()
            if not sender_account:
                raise HTTPException(status_code=404, detail="Sender account not found")
            
            if recipient_acc.id == sender_account.id:
                raise HTTPException(status_code=400, detail="Cannot transfer to your own account")
            
            # Process debit from sender
            debit_result = self.process_transaction(
                user=user,
                amount=amount,
                transaction_type="debit",
                description=f"Transfer to {recipient_account}: {description}",
                recipient_account=recipient_account
            )
            
            # Process credit to recipient
            recipient_user = self.db.query(User).filter(User.id == recipient_acc.user_id).first()
            if not recipient_user:
                raise HTTPException(status_code=404, detail="Recipient user not found")
            
            credit_result = self.process_transaction(
                user=recipient_user,
                amount=amount,
                transaction_type="credit",
                description=f"Transfer from {user.email}: {description}",
                recipient_account=sender_account.account_number
            )
            
            return {
                "success": True,
                "message": f"Successfully transferred ${amount:.2f} to account {recipient_account}",
                "debit_transaction": debit_result,
                "credit_transaction": credit_result
            }
            
        except HTTPException:
            raise
        except Exception as e:
            self.db.rollback()
            print(f"❌ Error transferring funds: {e}")
            raise HTTPException(status_code=500, detail="Failed to transfer funds")

# Dependency for easy use in endpoints
def get_transaction_service(db: Session = Depends(get_db)) -> TransactionService:
    return TransactionService(db)
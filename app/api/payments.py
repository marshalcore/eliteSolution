# app/api/payments.py

from fastapi import APIRouter, HTTPException, BackgroundTasks, Depends, Request
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.models.transaction import Transaction
from app.models.account import Account
from app.services.paystack_service import verify_paystack_transaction
from app.services.email_service import send_email

router = APIRouter(prefix="/api/v1/payments", tags=["payments"])

@router.post("/paystack-webhook")
async def paystack_webhook(request: Request, background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    """
    Endpoint to handle Paystack webhooks for successful transactions.
    """
    payload = await request.json()
    event = payload.get("event")

    if event == "charge.success":
        data = payload.get("data", {})
        reference = data.get("reference")

        # Find the transaction in our DB
        txn = db.query(Transaction).filter(Transaction.reference == reference).first()
        if not txn:
            return {"status": "ignored"}  # Transaction not found

        # Verify transaction via Paystack API
        try:
            verify = verify_paystack_transaction(reference)
            if verify.get("status") is True:
                # Credit the user's account
                acc = db.query(Account).filter(Account.id == txn.to_account_id).one_or_none()
                if acc:
                    acc.balance_cents += txn.amount_cents
                    txn.status = "completed"
                    db.commit()

                    # Send email in background
                    background_tasks.add_task(
                        send_email,
                        acc.user.email,
                        "Deposit completed",
                        f"Your deposit of {txn.amount_cents/100:.2f} has cleared."
                    )
                    return {"status": "ok"}
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

    return {"status": "handled"}

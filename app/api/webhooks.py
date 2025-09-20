# backend/app/api/webhooks.py
from fastapi import APIRouter, Request, BackgroundTasks, HTTPException, Depends
from sqlalchemy.orm import Session

from app.db import get_db
from app.models.transaction import Transaction
from app.models.account import Account
from app.services.paystack_service import verify_paystack_transaction
from app.services.email_service import send_email

router = APIRouter(prefix="/api/v1/webhooks", tags=["webhooks"])


@router.post("/paystack")
async def paystack_webhook(
    request: Request,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
):
    payload = await request.json()
    event = payload.get("event")

    if event == "charge.success":
        data = payload.get("data", {})
        ref = data.get("reference")
        txn = db.query(Transaction).filter(Transaction.reference == ref).first()

        if not txn:
            return {"status": "ignored"}

        # verify via API
        try:
            verify = verify_paystack_transaction(ref)
            if verify.get("status") is True:
                # credit
                acc = db.query(Account).filter(Account.id == txn.to_account_id).one_or_none()
                if acc:
                    acc.balance_cents += txn.amount_cents
                    txn.status = "completed"
                    db.commit()

                    # send email
                    background_tasks.add_task(
                        send_email,
                        acc.user.email,
                        "Deposit completed",
                        f"Your deposit of {txn.amount_cents/100:.2f} has cleared.",
                    )
                    return {"status": "ok"}
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

    return {"status": "handled"}

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.db import get_db
from app.services.okx_service import create_okx_deposit_address
from app.services.paystack_service import initialize_paystack_payment
from app.services.flutterwave_service import initialize_flutterwave_payment

router = APIRouter(prefix="/deposit", tags=["Deposit"])


@router.post("/okx")
async def deposit_okx(user_id: int, amount: float, db: Session = Depends(get_db)):
    """
    Create an OKX deposit address for the user.
    """
    try:
        result = await create_okx_deposit_address(user_id, amount)
        return {"provider": "OKX", "data": result}
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"OKX deposit error: {str(e)}")


@router.post("/paystack")
async def deposit_paystack(email: str, amount: float, db: Session = Depends(get_db)):
    """
    Initialize a Paystack payment.
    """
    try:
        result = await initialize_paystack_payment(email, amount)
        return {"provider": "Paystack", "data": result}
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Paystack error: {str(e)}")


@router.post("/flutterwave")
async def deposit_flutterwave(email: str, amount: float, db: Session = Depends(get_db)):
    """
    Initialize a Flutterwave payment.
    """
    try:
        result = await initialize_flutterwave_payment(email, amount)
        return {"provider": "Flutterwave", "data": result}
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Flutterwave error: {str(e)}")

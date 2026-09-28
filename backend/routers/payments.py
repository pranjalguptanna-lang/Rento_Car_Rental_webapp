from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field
import uuid

from backend.auth.dependencies import get_db, get_current_user
from backend.database.models import User, Booking, Payment, Notification

router = APIRouter(prefix="/payments", tags=["payments"])

class PaymentIntentRequest(BaseModel):
    booking_id: int
    amount: float = Field(..., gt=0)
    currency: str = "usd"
    payment_method_id: str = Field("pm_card_visa", description="Sandbox test payment method ID")

class PaymentRefundRequest(BaseModel):
    payment_id: int
    amount: float = Field(..., gt=0)
    reason: str = "Customer requested cancellation refund"

@router.post("/process-intent")
def process_payment_intent(
    req: PaymentIntentRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Sandbox/Test-mode payment gateway integration (Stripe API contract stub).
    Processes payment for booking without storing raw credit card details.
    """
    booking = db.query(Booking).filter(Booking.id == req.booking_id).first()
    if not booking:
        raise HTTPException(status_code=404, detail="Booking not found")

    # Create Payment record
    payment = Payment(amount=req.amount, status="succeeded")
    db.add(payment)
    db.commit()
    db.refresh(payment)

    booking.payment_id = payment.id
    db.commit()

    # Dispatch notification
    notif = Notification(
        user_id=current_user.id,
        message=f"Payment of ${req.amount:.2f} processed successfully for Booking #{booking.id} (Txn: txn_{uuid.uuid4().hex[:10]})."
    )
    db.add(notif)
    db.commit()

    return {
        "payment_id": payment.id,
        "booking_id": booking.id,
        "status": "succeeded",
        "transaction_id": f"txn_{uuid.uuid4().hex[:12]}",
        "receipt_url": f"https://pay.rento.com/receipts/rec_{uuid.uuid4().hex[:8]}"
    }

@router.post("/refund")
def process_payment_refund(
    req: PaymentRefundRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    payment = db.query(Payment).filter(Payment.id == req.payment_id).first()
    if not payment:
        raise HTTPException(status_code=404, detail="Payment record not found")

    payment.status = "refunded"
    db.commit()

    notif = Notification(
        user_id=current_user.id,
        message=f"Refund of ${req.amount:.2f} issued for Payment #{payment.id}."
    )
    db.add(notif)
    db.commit()

    return {
        "payment_id": payment.id,
        "refund_id": f"ref_{uuid.uuid4().hex[:10]}",
        "amount_refunded": req.amount,
        "status": "refunded"
    }

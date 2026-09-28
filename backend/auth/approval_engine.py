from enum import Enum
from backend.database.models import BookingStatusEnum

class ApprovalDecision(str, Enum):
    AUTO_APPROVE = "auto_approve"
    MANUAL_REVIEW = "manual_review"
    REJECT = "reject"

def evaluate_booking_approval(trust_score: float, payment_verified: bool, car_health_score: float) -> ApprovalDecision:
    """
    Evaluates booking request based on Decision Table/Tree Rules (R1 - R6):
    - R1: Trust Score >= 80 + payment verified + Car Health Score >= 70 -> auto_approve
    - R2: Trust Score >= 80 + payment not verified -> manual_review
    - R3: Trust Score 50-79 + Car Health Score < 70 -> manual_review
    - R4: Trust Score 50-79 + payment not verified -> reject
    - R5: Trust Score 50-79 + payment verified + Car Health Score >= 70 -> manual_review
    - R6: Trust Score < 50 -> reject
    """
    if trust_score < 50:
        return ApprovalDecision.REJECT

    if 50 <= trust_score <= 79:
        if not payment_verified:
            return ApprovalDecision.REJECT
        # Payment is verified but score is in medium trust range
        return ApprovalDecision.MANUAL_REVIEW

    # trust_score >= 80
    if not payment_verified:
        return ApprovalDecision.MANUAL_REVIEW

    if car_health_score < 70:
        return ApprovalDecision.MANUAL_REVIEW

    return ApprovalDecision.AUTO_APPROVE

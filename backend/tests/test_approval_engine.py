import pytest
from backend.auth.approval_engine import evaluate_booking_approval, ApprovalDecision

def test_rule_1_auto_approve():
    # Trust Score >= 80 + payment verified + Car Health Score >= 70 -> auto_approve
    res = evaluate_booking_approval(trust_score=85.0, payment_verified=True, car_health_score=90.0)
    assert res == ApprovalDecision.AUTO_APPROVE

def test_rule_2_manual_review_unverified_payment_high_trust():
    # Trust Score >= 80 + payment not verified -> manual_review
    res = evaluate_booking_approval(trust_score=85.0, payment_verified=False, car_health_score=90.0)
    assert res == ApprovalDecision.MANUAL_REVIEW

def test_rule_3_manual_review_low_car_health():
    # Trust Score >= 80 + payment verified + Car Health Score < 70 -> manual_review
    res = evaluate_booking_approval(trust_score=85.0, payment_verified=True, car_health_score=65.0)
    assert res == ApprovalDecision.MANUAL_REVIEW

def test_rule_4_reject_medium_trust_unverified_payment():
    # Trust Score 50-79 + payment not verified -> reject
    res = evaluate_booking_approval(trust_score=65.0, payment_verified=False, car_health_score=80.0)
    assert res == ApprovalDecision.REJECT

def test_rule_5_manual_review_medium_trust():
    # Trust Score 50-79 + payment verified -> manual_review
    res = evaluate_booking_approval(trust_score=70.0, payment_verified=True, car_health_score=80.0)
    assert res == ApprovalDecision.MANUAL_REVIEW

def test_rule_6_reject_low_trust():
    # Trust Score < 50 -> always reject
    res = evaluate_booking_approval(trust_score=40.0, payment_verified=True, car_health_score=100.0)
    assert res == ApprovalDecision.REJECT

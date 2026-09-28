from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from datetime import datetime

from backend.auth.dependencies import get_db, get_current_user, require_role
from backend.database.models import User, RoleEnum, Vehicle, Booking, BookingStatusEnum
from backend.schemas.booking import BookingCreate, BookingStatusUpdate, BookingResponse

router = APIRouter(prefix="/bookings", tags=["bookings"])

# Valid state transitions machine map
VALID_TRANSITIONS = {
    BookingStatusEnum.created: {BookingStatusEnum.pending_approval, BookingStatusEnum.cancelled},
    BookingStatusEnum.pending_approval: {BookingStatusEnum.confirmed, BookingStatusEnum.rejected, BookingStatusEnum.cancelled},
    BookingStatusEnum.confirmed: {BookingStatusEnum.pickup_inspection, BookingStatusEnum.cancelled},
    BookingStatusEnum.pickup_inspection: {BookingStatusEnum.ongoing_trip, BookingStatusEnum.cancelled},
    BookingStatusEnum.ongoing_trip: {BookingStatusEnum.return_inspection, BookingStatusEnum.disputed},
    BookingStatusEnum.return_inspection: {BookingStatusEnum.completed, BookingStatusEnum.disputed},
    BookingStatusEnum.disputed: {BookingStatusEnum.resolved},
    BookingStatusEnum.completed: set(),
    BookingStatusEnum.rejected: set(),
    BookingStatusEnum.resolved: set(),
    BookingStatusEnum.cancelled: set(),
}

@router.post("", response_model=BookingResponse, status_code=status.HTTP_201_CREATED)
def create_booking(
    booking_in: BookingCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(RoleEnum.renter))
):
    vehicle = db.query(Vehicle).filter(Vehicle.id == booking_in.vehicle_id, Vehicle.is_active == True).first()
    if not vehicle:
        raise HTTPException(status_code=404, detail="Vehicle not found or inactive")
    
    if booking_in.end_date <= booking_in.start_date:
        raise HTTPException(status_code=400, detail="End date must be after start date")
        
    import json
    from backend.schemas.booking import EXTRAS_PRICING

    days = max(1, (booking_in.end_date - booking_in.start_date).days)
    base_vehicle_cost = vehicle.price_per_day * days
    
    # Calculate bundled extras cost
    extras_cost = 0.0
    valid_extras = []
    if booking_in.bundled_extras:
        for extra in booking_in.bundled_extras:
            if extra in EXTRAS_PRICING:
                extras_cost += EXTRAS_PRICING[extra]
                valid_extras.append(extra)

    total_price = base_vehicle_cost + extras_cost
    deposit = total_price * 0.2

    # Itemized cost-splitting logic
    participants_count = max(1, booking_in.participants_count)
    if booking_in.custom_split_ratios:
        total_ratio = sum(booking_in.custom_split_ratios.values())
        split_map = {p: round((ratio / total_ratio) * total_price, 2) for p, ratio in booking_in.custom_split_ratios.items()}
    else:
        per_person = round(total_price / participants_count, 2)
        split_map = {f"Participant_{i+1}": per_person for i in range(participants_count)}

    from backend.auth.approval_engine import evaluate_booking_approval, ApprovalDecision
    from backend.database.models import TrustScore

    # Query renter trust score & payment verification state
    user_ts = db.query(TrustScore).filter(TrustScore.user_id == current_user.id).first()
    ts_val = user_ts.score if user_ts else 70.0
    payment_verified = True # Simulated default
    car_health = vehicle.health_score or 100.0

    decision = evaluate_booking_approval(ts_val, payment_verified, car_health)
    
    if decision == ApprovalDecision.AUTO_APPROVE:
        initial_status = BookingStatusEnum.confirmed
    elif decision == ApprovalDecision.MANUAL_REVIEW:
        initial_status = BookingStatusEnum.pending_approval
    else:
        raise HTTPException(
            status_code=400,
            detail=f"Booking rejected automatically due to low renter trust score ({ts_val}) or risk policy"
        )

    new_booking = Booking(
        renter_id=current_user.id,
        vehicle_id=vehicle.id,
        start_date=booking_in.start_date,
        end_date=booking_in.end_date,
        total_price=total_price,
        deposit_amount=deposit,
        status=initial_status,
        participants_count=participants_count,
        bundled_extras=json.dumps(valid_extras),
        cost_split_details=json.dumps(split_map)
    )
    db.add(new_booking)
    db.commit()
    db.refresh(new_booking)
    return new_booking



@router.get("", response_model=List[BookingResponse])
def get_user_bookings(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    if current_user.role == RoleEnum.admin:
        return db.query(Booking).all()
    elif current_user.role == RoleEnum.host:
        return db.query(Booking).join(Vehicle).filter(Vehicle.host_id == current_user.id).all()
    else:
        return db.query(Booking).filter(Booking.renter_id == current_user.id).all()

@router.get("/{booking_id}", response_model=BookingResponse)
def get_booking(
    booking_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    booking = db.query(Booking).filter(Booking.id == booking_id).first()
    if not booking:
        raise HTTPException(status_code=404, detail="Booking not found")

    # Authorization check
    if current_user.role == RoleEnum.renter and booking.renter_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized to access this booking")
    if current_user.role == RoleEnum.host and booking.vehicle.host_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized to access this booking")

    return booking

@router.patch("/{booking_id}/status", response_model=BookingResponse)
def update_booking_status(
    booking_id: int,
    status_update: BookingStatusUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    booking = db.query(Booking).filter(Booking.id == booking_id).first()
    if not booking:
        raise HTTPException(status_code=404, detail="Booking not found")

    target_status = status_update.status
    current_status = booking.status

    if target_status not in VALID_TRANSITIONS.get(current_status, set()):
        raise HTTPException(
            status_code=400,
            detail=f"Invalid state transition from {current_status.value} to {target_status.value}"
        )

    booking.status = target_status
    db.commit()
    db.refresh(booking)
    return booking

@router.post("/{booking_id}/cancel", response_model=BookingResponse)
def cancel_booking(
    booking_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    booking = db.query(Booking).filter(Booking.id == booking_id).first()
    if not booking:
        raise HTTPException(status_code=404, detail="Booking not found")

    if current_user.role == RoleEnum.renter and booking.renter_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized to cancel this booking")

    # Only pre-pickup cancellation allowed
    pre_pickup_statuses = {
        BookingStatusEnum.created,
        BookingStatusEnum.pending_approval,
        BookingStatusEnum.confirmed
    }
    if booking.status not in pre_pickup_statuses:
        raise HTTPException(
            status_code=400,
            detail=f"Cannot cancel booking once pickup inspection or trip has started (current status: {booking.status.value})"
        )

    booking.status = BookingStatusEnum.cancelled
    db.commit()
    db.refresh(booking)
    return booking

@router.post("/{booking_id}/telematics")
def ingest_trip_telematics(
    booking_id: int,
    data_points: List[dict],
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    booking = db.query(Booking).filter(Booking.id == booking_id).first()
    if not booking:
        raise HTTPException(status_code=404, detail="Booking not found")

    from ai_services.telematics_service.main import process_telematics_stream, TelematicsStreamRequest, TelematicsDataPoint
    from backend.database.models import Trip

    pts = [TelematicsDataPoint(**pt) for pt in data_points]
    req = TelematicsStreamRequest(trip_id=booking_id, data_points=pts)
    res = process_telematics_stream(req)

    # Attach/Update Trip record
    if not booking.trip:
        trip = Trip(safety_score=res.safety_score, telematics_log=res.summary)
        db.add(trip)
        db.commit()
        db.refresh(trip)
        booking.trip_id = trip.id
    else:
        booking.trip.safety_score = res.safety_score
        booking.trip.telematics_log = res.summary

    db.commit()
    db.refresh(booking)
    return res


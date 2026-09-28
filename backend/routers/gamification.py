from typing import List
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from pydantic import BaseModel, ConfigDict

from backend.auth.dependencies import get_db, get_current_user
from backend.database.models import User, RoleEnum, Vehicle, Notification, Booking

router = APIRouter(prefix="/gamification", tags=["gamification"])

class HostRewardTierResponse(BaseModel):
    host_id: int
    points: int
    tier: str # Bronze, Silver, Gold
    cleanliness_avg_rating: float
    cancellation_rate_pct: float
    response_time_mins: int
    perks: List[str]

    model_config = ConfigDict(from_attributes=True)

class CarbonScoreResponse(BaseModel):
    vehicle_id: int
    vehicle_is_ev: bool
    distance_miles: float
    co2_emissions_saved_kg: float
    eco_tier: str
    points_awarded: int

    model_config = ConfigDict(from_attributes=True)

@router.get("/host/{host_id}/rewards", response_model=HostRewardTierResponse)
def get_host_rewards(
    host_id: int,
    db: Session = Depends(get_db)
):
    host = db.query(User).filter(User.id == host_id, User.role == RoleEnum.host).first()
    if not host:
        raise HTTPException(status_code=404, detail="Host user not found")

    # Mock/Calculated Host Metrics
    cleanliness = 4.8
    cancel_rate = 1.2 # 1.2%
    resp_time = 15 # mins

    # Points formula: cleanliness * 100 - cancel_rate * 10
    points = int((cleanliness * 100) - (cancel_rate * 10))

    if points >= 450:
        tier = "Gold"
        perks = ["0% commission fee boost", "Priority search placement", "Gold Host Badge"]
    elif points >= 350:
        tier = "Silver"
        perks = ["5% commission reduction", "Silver Host Badge"]
    else:
        tier = "Bronze"
        perks = ["Standard listing"]

    return HostRewardTierResponse(
        host_id=host.id,
        points=points,
        tier=tier,
        cleanliness_avg_rating=cleanliness,
        cancellation_rate_pct=cancel_rate,
        response_time_mins=resp_time,
        perks=perks
    )

@router.get("/carbon-score", response_model=CarbonScoreResponse)
def calculate_carbon_score(
    vehicle_id: int,
    distance_miles: float = Query(..., gt=0),
    db: Session = Depends(get_db)
):
    vehicle = db.query(Vehicle).filter(Vehicle.id == vehicle_id).first()
    if not vehicle:
        raise HTTPException(status_code=404, detail="Vehicle not found")

    # Average gas car produces ~0.404 kg CO2 per mile
    # EV produces ~0.050 kg CO2 equivalent (grid average) per mile -> saves ~0.354 kg/mile
    if vehicle.is_ev:
        saved_kg = round(distance_miles * 0.354, 2)
        eco_tier = "Eco Champion (EV)"
        pts = int(distance_miles * 2)
    else:
        saved_kg = 0.0
        eco_tier = "Standard ICE Vehicle"
        pts = int(distance_miles * 0.5)

    return CarbonScoreResponse(
        vehicle_id=vehicle.id,
        vehicle_is_ev=vehicle.is_ev,
        distance_miles=distance_miles,
        co2_emissions_saved_kg=saved_kg,
        eco_tier=eco_tier,
        points_awarded=pts
    )

@router.get("/notifications", response_model=List[dict])
def get_user_notifications(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    notifs = db.query(Notification).filter(Notification.user_id == current_user.id).order_by(Notification.created_at.desc()).all()
    return [{"id": n.id, "message": n.message, "is_read": n.is_read, "created_at": n.created_at.isoformat()} for n in notifs]

from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query, UploadFile, File
from sqlalchemy.orm import Session
from sqlalchemy import and_

from backend.auth.dependencies import get_db, get_current_user, require_role
from backend.database.models import User, RoleEnum, Vehicle, EVDetails, Hub
from backend.schemas.vehicle import VehicleCreate, VehicleUpdate, VehicleResponse

router = APIRouter(prefix="/vehicles", tags=["vehicles"])

@router.post("", response_model=VehicleResponse, status_code=status.HTTP_201_CREATED)
def create_listing(
    vehicle_in: VehicleCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(RoleEnum.host))
):
    new_vehicle = Vehicle(
        host_id=current_user.id,
        hub_id=vehicle_in.hub_id,
        make=vehicle_in.make,
        model=vehicle_in.model,
        is_ev=vehicle_in.is_ev,
        price_per_day=vehicle_in.price_per_day
    )
    db.add(new_vehicle)
    db.commit()
    db.refresh(new_vehicle)

    if vehicle_in.is_ev and vehicle_in.ev_details:
        ev_det = EVDetails(
            vehicle_id=new_vehicle.id,
            battery_capacity=vehicle_in.ev_details.battery_capacity,
            charging_type=vehicle_in.ev_details.charging_type
        )
        db.add(ev_det)
        db.commit()
        db.refresh(new_vehicle) # Reload relations

    return new_vehicle

@router.put("/{vehicle_id}", response_model=VehicleResponse)
def update_listing(
    vehicle_id: int,
    vehicle_update: VehicleUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(RoleEnum.host))
):
    vehicle = db.query(Vehicle).filter(Vehicle.id == vehicle_id, Vehicle.host_id == current_user.id).first()
    if not vehicle:
        raise HTTPException(status_code=404, detail="Vehicle not found or not owned by you")

    if vehicle_update.price_per_day is not None:
        vehicle.price_per_day = vehicle_update.price_per_day
    if vehicle_update.hub_id is not None:
        vehicle.hub_id = vehicle_update.hub_id

    db.commit()
    db.refresh(vehicle)
    return vehicle

@router.delete("/{vehicle_id}", status_code=status.HTTP_204_NO_CONTENT)
def soft_delete_listing(
    vehicle_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(RoleEnum.host))
):
    vehicle = db.query(Vehicle).filter(Vehicle.id == vehicle_id, Vehicle.host_id == current_user.id).first()
    if not vehicle:
        raise HTTPException(status_code=404, detail="Vehicle not found or not owned by you")

    vehicle.is_active = False
    db.commit()
    return None

@router.post("/{vehicle_id}/photos")
def upload_photos(
    vehicle_id: int,
    files: List[UploadFile] = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(RoleEnum.host))
):
    vehicle = db.query(Vehicle).filter(Vehicle.id == vehicle_id, Vehicle.host_id == current_user.id).first()
    if not vehicle:
        raise HTTPException(status_code=404, detail="Vehicle not found or not owned by you")
    
    fake_urls = [f"https://cdn.rento.com/vehicles/{vehicle_id}/photo_{f.filename}" for f in files]
    return {"msg": "Photos uploaded successfully", "urls": fake_urls}

@router.get("", response_model=List[VehicleResponse])
def search_vehicles(
    min_price: Optional[float] = Query(None),
    max_price: Optional[float] = Query(None),
    is_ev: Optional[bool] = Query(None),
    location: Optional[str] = Query(None),
    db: Session = Depends(get_db)
):
    query = db.query(Vehicle).filter(Vehicle.is_active == True)
    
    if min_price is not None:
        query = query.filter(Vehicle.price_per_day >= min_price)
    if max_price is not None:
        query = query.filter(Vehicle.price_per_day <= max_price)
    if is_ev is not None:
        query = query.filter(Vehicle.is_ev == is_ev)

    if location is not None:
        query = query.join(Hub).filter(Hub.location.ilike(f"%{location}%"))

    return query.all()

@router.get("/{vehicle_id}/recommend-price")
def recommend_vehicle_price(
    vehicle_id: int,
    db: Session = Depends(get_db)
):
    vehicle = db.query(Vehicle).filter(Vehicle.id == vehicle_id).first()
    if not vehicle:
        raise HTTPException(status_code=404, detail="Vehicle not found")

    # Import and call pricing microservice logic directly or via request
    from ai_services.pricing_service.main import recommend_price, PricingRequest
    
    city_name = vehicle.hub.location if vehicle.hub else "San Francisco"
    req = PricingRequest(
        base_price=vehicle.price_per_day,
        city=city_name,
        active_bookings_in_city=6
    )
    return recommend_price(req)

@router.get("/search/match")
def search_matching_vehicles(
    q: str = Query(..., description="Natural language search query"),
    db: Session = Depends(get_db)
):
    vehicles = db.query(Vehicle).filter(Vehicle.is_active == True).all()
    if not vehicles:
        return {"query": q, "matches": []}

    from ai_services.matching_service.main import match_vehicles, MatchRequest, VehicleMetadata
    
    vehicle_metas = [
        VehicleMetadata(
            id=v.id,
            make=v.make,
            model=v.model,
            is_ev=v.is_ev,
            price_per_day=v.price_per_day,
            location=v.hub.location if v.hub else "",
            extras=["child seat"] if "model 3" in v.model.lower() or "leaf" in v.model.lower() else [],
            description=f"{v.make} {v.model}"
        ) for v in vehicles
    ]
    
    req = MatchRequest(query=q, vehicles=vehicle_metas, top_k=10)
    return match_vehicles(req)

@router.get("/{vehicle_id}/health-score")
def get_vehicle_health_score(
    vehicle_id: int,
    db: Session = Depends(get_db)
):
    vehicle = db.query(Vehicle).filter(Vehicle.id == vehicle_id).first()
    if not vehicle:
        raise HTTPException(status_code=404, detail="Vehicle not found")

    from ai_services.scoring_service.main import calculate_health_score, CarHealthRequest
    
    req = CarHealthRequest(
        vehicle_id=vehicle.id,
        mileage=25000.0,
        days_since_last_service=45,
        condition_flags=[],
        inspection_damage_flags=[]
    )
    result = calculate_health_score(req)
    
    # Update score on Vehicle record
    vehicle.health_score = result.health_score
    db.commit()
    db.refresh(vehicle)
    
    return result

@router.get("/{vehicle_id}/ev-guidance")

def check_ev_range_and_charging(
    vehicle_id: int,
    trip_distance_miles: float = Query(..., gt=0, description="Planned trip distance in miles"),
    current_charge_pct: float = Query(100.0, ge=0, le=100, description="Current battery state of charge percentage"),
    db: Session = Depends(get_db)
):
    vehicle = db.query(Vehicle).filter(Vehicle.id == vehicle_id).first()
    if not vehicle:
        raise HTTPException(status_code=404, detail="Vehicle not found")

    if not vehicle.is_ev or not vehicle.ev_details:
        raise HTTPException(status_code=400, detail="Vehicle is not an EV or lacks EV details")

    ev = vehicle.ev_details
    # Standard efficiency assumption: ~3.5 miles per kWh
    efficiency = 3.5
    full_range = ev.battery_capacity * efficiency
    usable_range = round(full_range * (current_charge_pct / 100.0), 2)

    is_feasible = usable_range >= trip_distance_miles

    charging_stops = []
    if not is_feasible:
        # Mock EV Charging Station recommendations along the route
        deficit_miles = trip_distance_miles - usable_range
        charging_stops = [
            {
                "name": "Supercharger Hub Alpha - Mile 80",
                "location": "Interstate 80 Exit 12",
                "charging_type": ev.charging_type,
                "recommended_charge_mins": 25,
                "estimated_range_added_miles": round(deficit_miles + 30.0, 1)
            },
            {
                "name": "EcoCharge FastStation - Mile 140",
                "location": "Highway 101 Station 4",
                "charging_type": ev.charging_type,
                "recommended_charge_mins": 20,
                "estimated_range_added_miles": round(deficit_miles + 10.0, 1)
            }
        ]

    return {
        "vehicle_id": vehicle.id,
        "battery_capacity_kwh": ev.battery_capacity,
        "current_charge_pct": current_charge_pct,
        "usable_range_miles": usable_range,
        "trip_distance_miles": trip_distance_miles,
        "is_trip_feasible_without_charging": is_feasible,
        "recommended_charging_stops": charging_stops,
        "guidance_message": "Trip feasible on current charge!" if is_feasible else f"Charging stop required. Current range ({usable_range} mi) is insufficient for planned trip ({trip_distance_miles} mi)."
    }





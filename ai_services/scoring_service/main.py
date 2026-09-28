import datetime
from typing import List, Optional
from fastapi import FastAPI
from pydantic import BaseModel, Field, ConfigDict

app = FastAPI(title="Rento Car Health Score (CHS) Microservice")

class CarHealthRequest(BaseModel):
    vehicle_id: int
    mileage: float = Field(default=20000.0, ge=0, description="Odometer reading in miles")
    days_since_last_service: int = Field(default=30, ge=0, description="Days elapsed since last scheduled maintenance")
    condition_flags: Optional[List[str]] = Field(default_factory=list, description="Host-declared flags e.g. 'scratch', 'check_engine_light', 'tire_wear'")
    inspection_damage_flags: Optional[List[str]] = Field(default_factory=list, description="Damage flags derived from visual inspections")

class CarHealthResponse(BaseModel):
    vehicle_id: int
    health_score: float
    deductions: dict
    status_summary: str

    model_config = ConfigDict(from_attributes=True)

@app.post("/calculate-health-score", response_model=CarHealthResponse)
def calculate_health_score(req: CarHealthRequest):
    """
    Computes a Car Health Score (CHS) from 0 to 100 based on weighted deductions:
    - Base score: 100.0
    - Mileage deduction: -1 point per 10,000 miles over 30,000 miles (max -20)
    - Service overdue deduction: -0.1 points per day over 180 days (max -30)
    - Condition flags: -10 points per flag
    - Inspection damage flags: -15 points per flag
    """
    base_score = 100.0
    deductions = {}

    # 1. Mileage deduction
    if req.mileage > 30000:
        excess_mileage = req.mileage - 30000
        mileage_ded = min(20.0, round((excess_mileage / 10000.0) * 1.5, 2))
        deductions["mileage"] = mileage_ded
    else:
        deductions["mileage"] = 0.0

    # 2. Service overdue deduction
    if req.days_since_last_service > 180:
        overdue_days = req.days_since_last_service - 180
        service_ded = min(30.0, round(overdue_days * 0.1, 2))
        deductions["service_overdue"] = service_ded
    else:
        deductions["service_overdue"] = 0.0

    # 3. Host condition flags
    cond_count = len(req.condition_flags or [])
    cond_ded = min(30.0, cond_count * 10.0)
    deductions["condition_flags"] = cond_ded

    # 4. Inspection damage flags
    insp_count = len(req.inspection_damage_flags or [])
    insp_ded = min(40.0, insp_count * 15.0)
    deductions["inspection_damage"] = insp_ded

    total_deduction = sum(deductions.values())
    final_score = max(0.0, round(base_score - total_deduction, 2))

    if final_score >= 85:
        summary = "Excellent car health"
    elif final_score >= 70:
        summary = "Good car health"
    elif final_score >= 50:
        summary = "Fair - requires attention"
    else:
        summary = "Poor car health - maintenance required"

    return CarHealthResponse(
        vehicle_id=req.vehicle_id,
        health_score=final_score,
        deductions=deductions,
        status_summary=summary
    )

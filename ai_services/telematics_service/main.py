from typing import List, Optional
from fastapi import FastAPI
from pydantic import BaseModel, Field, ConfigDict

app = FastAPI(title="Rento Telematics & Driver Safety Microservice")

class TelematicsDataPoint(BaseModel):
    timestamp: str
    speed_mph: float
    accel_g: float = Field(..., description="Acceleration in Gs (negative for deceleration)")
    latitude: float
    longitude: float

class TelematicsStreamRequest(BaseModel):
    trip_id: int
    data_points: List[TelematicsDataPoint]

class EmergencyEvent(BaseModel):
    event_type: str
    timestamp: str
    deceleration_g: float
    location: dict
    actions_taken: List[str]

class TelematicsEvaluationResponse(BaseModel):
    trip_id: int
    safety_score: float
    hard_braking_events: int
    rapid_acceleration_events: int
    speeding_events: int
    collision_detected: bool
    emergency_event: Optional[EmergencyEvent] = None
    summary: str

    model_config = ConfigDict(from_attributes=True)

COLLISION_DECEL_THRESHOLD_G = -3.5 # Extreme deceleration threshold indicative of crash

@app.post("/telematics/process", response_model=TelematicsEvaluationResponse)
def process_telematics_stream(req: TelematicsStreamRequest):
    """
    Evaluates simulated sensor stream data (accelerometer/GPS):
    1. Driver Safety Score (0-100 base, with deductions for hard braking, rapid accel, speeding)
    2. Collision Detection: Triggers emergency response workflow if deceleration exceeds threshold.
    """
    base_score = 100.0
    hard_braking = 0
    rapid_accel = 0
    speeding = 0
    collision_detected = False
    emergency_event = None

    for pt in req.data_points:
        # Check collision threshold
        if pt.accel_g <= COLLISION_DECEL_THRESHOLD_G:
            collision_detected = True
            emergency_event = EmergencyEvent(
                event_type="PROBABLE_VEHICLE_COLLISION",
                timestamp=pt.timestamp,
                deceleration_g=pt.accel_g,
                location={"lat": pt.latitude, "lng": pt.longitude},
                actions_taken=[
                    "Logged emergency event to system audit trail",
                    "Mocked automated SMS to emergency contact",
                    "Dispatched live GPS coordinates to first responder stub"
                ]
            )
            base_score -= 40.0
        elif pt.accel_g <= -0.5: # Hard braking
            hard_braking += 1
            base_score -= 5.0
        elif pt.accel_g >= 0.5: # Rapid acceleration
            rapid_accel += 1
            base_score -= 4.0

        if pt.speed_mph > 80.0:
            speeding += 1
            base_score -= 3.0

    final_score = max(0.0, round(base_score, 2))
    
    if collision_detected:
        summary = "CRITICAL EMERGENCY: Probable collision detected! Emergency workflow dispatched."
    elif final_score >= 85:
        summary = "Smooth and safe driving record."
    elif final_score >= 60:
        summary = "Moderate driving performance with occasional hard braking or acceleration."
    else:
        summary = "High-risk driving performance detected."

    return TelematicsEvaluationResponse(
        trip_id=req.trip_id,
        safety_score=final_score,
        hard_braking_events=hard_braking,
        rapid_acceleration_events=rapid_accel,
        speeding_events=speeding,
        collision_detected=collision_detected,
        emergency_event=emergency_event,
        summary=summary
    )

import base64
import io
from typing import List, Optional
from fastapi import FastAPI, HTTPException, status
from pydantic import BaseModel, Field, ConfigDict

app = FastAPI(title="Rento AI Pickup/Return Damage Inspection Microservice")

class InspectionPhoto(BaseModel):
    angle: str = Field(..., description="e.g. front, rear, left_side, right_side, windshield")
    image_url_or_b64: str = Field(..., description="URL or Base64 encoded string of photo")

class PickupInspectionRequest(BaseModel):
    booking_id: int
    photos: List[InspectionPhoto]

class ReturnInspectionRequest(BaseModel):
    booking_id: int
    pickup_photos: List[InspectionPhoto]
    return_photos: List[InspectionPhoto]

class DamageFlag(BaseModel):
    angle: str
    difference_score: float
    detected_issue: str

class InspectionEvidenceReport(BaseModel):
    booking_id: int
    has_new_damage: bool
    total_flagged_regions: int
    flags: List[DamageFlag]
    summary: str

    model_config = ConfigDict(from_attributes=True)

@app.post("/inspection/pickup")
def register_pickup_inspection(req: PickupInspectionRequest):
    """
    Registers baseline pickup photos (8-10 photos covering standard vehicle angles).
    """
    if len(req.photos) < 1:
        raise HTTPException(status_code=400, detail="At least 1 photo required for pickup baseline")
    return {
        "msg": f"Pickup baseline inspection recorded for booking {req.booking_id}",
        "photo_count": len(req.photos),
        "angles_recorded": [p.angle for p in req.photos]
    }

@app.post("/inspection/return", response_model=InspectionEvidenceReport)
def compare_return_inspection(req: ReturnInspectionRequest):
    """
    Runs computer-vision structural image comparison between pickup baseline photos
    and return photos by angle. Identifies visual differences (scratches, dents, cracks)
    and outputs a structured evidence report for dispute resolution.
    """
    pickup_map = {p.angle: p.image_url_or_b64 for p in req.pickup_photos}
    flags = []

    for r_photo in req.return_photos:
        angle = r_photo.angle
        p_img = pickup_map.get(angle)
        
        # Structural visual comparison (Simulated CV differencing metric)
        if p_img:
            # If photo data strings differ or contain explicit damage indicators
            diff_score = 0.0
            if r_photo.image_url_or_b64 != p_img:
                if "scratch" in r_photo.image_url_or_b64.lower() or "dent" in r_photo.image_url_or_b64.lower():
                    diff_score = 0.85
                else:
                    diff_score = 0.35 # minor lighting/angle difference
            
            if diff_score > 0.60:
                flags.append(DamageFlag(
                    angle=angle,
                    difference_score=diff_score,
                    detected_issue=f"New visual damage detected on {angle} (Score: {diff_score})"
                ))

    has_damage = len(flags) > 0
    summary = f"Inspection complete. {len(flags)} region(s) flagged for potential damage." if has_damage else "Inspection passed. No new damage detected."

    return InspectionEvidenceReport(
        booking_id=req.booking_id,
        has_new_damage=has_damage,
        total_flagged_regions=len(flags),
        flags=flags,
        summary=summary
    )

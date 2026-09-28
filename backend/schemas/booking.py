from typing import Optional, List, Dict
from datetime import datetime
from pydantic import BaseModel, Field, ConfigDict
from backend.database.models import BookingStatusEnum

EXTRAS_PRICING = {
    "child_seat": 15.0,
    "wifi": 10.0,
    "camping_kit": 35.0,
    "roof_rack": 20.0
}

class BookingCreate(BaseModel):
    vehicle_id: int
    start_date: datetime
    end_date: datetime
    participants_count: int = Field(default=1, ge=1, description="Number of participants sharing the booking")
    bundled_extras: Optional[List[str]] = Field(default_factory=list, description="Add-ons e.g. child_seat, wifi")
    custom_split_ratios: Optional[Dict[str, float]] = Field(default=None, description="Optional custom split dict mapping email/participant to ratio e.g. {'user1': 0.5, 'user2': 0.5}")

class BookingStatusUpdate(BaseModel):
    status: BookingStatusEnum

class BookingResponse(BaseModel):
    id: int
    renter_id: int
    vehicle_id: int
    start_date: datetime
    end_date: datetime
    total_price: float
    deposit_amount: float
    status: BookingStatusEnum
    participants_count: int
    bundled_extras: Optional[str] = None
    cost_split_details: Optional[str] = None
    payment_id: Optional[int] = None
    pickup_inspection_id: Optional[int] = None
    return_inspection_id: Optional[int] = None
    trip_id: Optional[int] = None

    model_config = ConfigDict(from_attributes=True)


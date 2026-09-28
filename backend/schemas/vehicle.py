from pydantic import BaseModel
from typing import Optional, List

class EVDetailsBase(BaseModel):
    battery_capacity: float
    charging_type: str

class EVDetailsCreate(EVDetailsBase):
    pass

class EVDetailsResponse(EVDetailsBase):
    id: int
    vehicle_id: int
    class Config:
        from_attributes = True

class HubResponse(BaseModel):
    id: int
    name: str
    location: str
    class Config:
        from_attributes = True

class VehicleBase(BaseModel):
    make: str
    model: str
    hub_id: Optional[int] = None
    is_ev: bool = False
    price_per_day: float

class VehicleCreate(VehicleBase):
    ev_details: Optional[EVDetailsCreate] = None

class VehicleUpdate(BaseModel):
    price_per_day: Optional[float] = None
    hub_id: Optional[int] = None

class VehicleResponse(VehicleBase):
    id: int
    host_id: int
    health_score: float
    is_active: bool
    ev_details: Optional[EVDetailsResponse] = None
    hub: Optional[HubResponse] = None

    class Config:
        from_attributes = True

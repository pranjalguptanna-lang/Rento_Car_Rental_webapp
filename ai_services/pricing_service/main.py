import datetime
from fastapi import FastAPI, HTTPException, status
from pydantic import BaseModel, Field, ConfigDict
from typing import Optional

app = FastAPI(title="Rento AI Dynamic Pricing Microservice")

class PricingRequest(BaseModel):
    base_price: float = Field(..., gt=0, description="Base daily rate for the vehicle")
    target_date: Optional[datetime.date] = Field(default_factory=datetime.date.today)
    city: Optional[str] = "San Francisco"
    active_bookings_in_city: int = Field(default=5, ge=0)
    is_holiday: Optional[bool] = False
    mock_weather: Optional[str] = Field(default="clear", description="clear, rainy, stormy, snow")

class PricingResponse(BaseModel):
    recommended_price: float
    base_price: float
    multipliers: dict
    explanation: str

    model_config = ConfigDict(from_attributes=True)

# Static mock list of major holidays for fallback
MOCK_HOLIDAYS = {
    (1, 1),   # New Year's Day
    (7, 4),   # Independence Day
    (11, 26), # Thanksgiving (approx)
    (12, 25), # Christmas
}

@app.post("/recommend-price", response_model=PricingResponse)
def recommend_price(req: PricingRequest):
    """
    Recommends an adjusted price per day based on:
    1. Day-of-week multiplier (weekend surge)
    2. Upcoming holiday flag
    3. Weather signal (clear vs adverse weather demand)
    4. City demand multiplier (based on active bookings count)
    
    Architecture Note:
    This rule-based engine can be seamlessly swapped for a trained ML regression model
    (e.g., XGBoost / LightGBM) by replacing internal calculation logic while retaining
    the exact same input schema and output contract.
    """
    target_date = req.target_date or datetime.date.today()
    multipliers = {}
    
    # 1. Day of week (0=Mon, 4=Fri, 5=Sat, 6=Sun)
    day_of_week = target_date.weekday()
    if day_of_week in (4, 5, 6): # Weekend surge
        day_mult = 1.25
        multipliers["day_of_week"] = day_mult
    else:
        day_mult = 1.00
        multipliers["day_of_week"] = day_mult

    # 2. Holiday multiplier
    is_holiday = req.is_holiday or (target_date.month, target_date.day) in MOCK_HOLIDAYS
    if is_holiday:
        holiday_mult = 1.30
        multipliers["holiday"] = holiday_mult
    else:
        holiday_mult = 1.00
        multipliers["holiday"] = holiday_mult

    # 3. Weather signal multiplier
    weather = (req.mock_weather or "clear").lower()
    if weather == "rainy":
        weather_mult = 1.10
    elif weather in ("stormy", "snow"):
        weather_mult = 0.85 # Bad weather dampens rental demand
    else:
        weather_mult = 1.00
    multipliers["weather"] = weather_mult

    # 4. Demand multiplier based on city active bookings
    if req.active_bookings_in_city > 20:
        demand_mult = 1.40
    elif req.active_bookings_in_city > 10:
        demand_mult = 1.20
    elif req.active_bookings_in_city > 5:
        demand_mult = 1.10
    else:
        demand_mult = 1.00
    multipliers["city_demand"] = demand_mult

    # Final price calculation
    total_multiplier = day_mult * holiday_mult * weather_mult * demand_mult
    recommended_price = round(req.base_price * total_multiplier, 2)

    explanation = (
        f"Base price ${req.base_price:.2f} adjusted by factor {total_multiplier:.2f} "
        f"(Weekend: {day_mult}x, Holiday: {holiday_mult}x, Weather: {weather_mult}x, Demand: {demand_mult}x)"
    )

    return PricingResponse(
        recommended_price=recommended_price,
        base_price=req.base_price,
        multipliers=multipliers,
        explanation=explanation
    )

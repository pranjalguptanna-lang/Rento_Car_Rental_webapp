import pytest
import datetime
from fastapi.testclient import TestClient
from ai_services.pricing_service.main import app

client = TestClient(app)




def test_pricing_recommendation_base():
    # Weekday, non-holiday, clear weather, low demand
    req_data = {
        "base_price": 100.0,
        "target_date": "2026-10-07", # Wednesday
        "city": "San Francisco",
        "active_bookings_in_city": 2,
        "is_holiday": False,
        "mock_weather": "clear"
    }
    res = client.post("/recommend-price", json=req_data)
    assert res.status_code == 200
    data = res.json()
    assert data["recommended_price"] == 100.0
    assert data["base_price"] == 100.0

def test_pricing_recommendation_surge():
    # Weekend, holiday, high demand
    req_data = {
        "base_price": 100.0,
        "target_date": "2026-07-04", # Independence Day (Saturday)
        "city": "San Francisco",
        "active_bookings_in_city": 25,
        "is_holiday": True,
        "mock_weather": "clear"
    }
    res = client.post("/recommend-price", json=req_data)
    assert res.status_code == 200
    data = res.json()
    # weekend 1.25 * holiday 1.30 * demand 1.40 = 2.275 -> $227.50
    assert data["recommended_price"] == 227.50
    assert data["multipliers"]["day_of_week"] == 1.25
    assert data["multipliers"]["holiday"] == 1.30
    assert data["multipliers"]["city_demand"] == 1.40

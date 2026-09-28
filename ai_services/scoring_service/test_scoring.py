import pytest
from fastapi.testclient import TestClient
from ai_services.scoring_service.main import app

client = TestClient(app)

def test_pristine_car_health_score():
    res = client.post("/calculate-health-score", json={
        "vehicle_id": 1,
        "mileage": 15000,
        "days_since_last_service": 60,
        "condition_flags": [],
        "inspection_damage_flags": []
    })
    assert res.status_code == 200
    data = res.json()
    assert data["health_score"] == 100.0
    assert data["status_summary"] == "Excellent car health"

def test_damaged_car_health_score():
    res = client.post("/calculate-health-score", json={
        "vehicle_id": 2,
        "mileage": 80000, # deduction 7.5
        "days_since_last_service": 240, # 60 days overdue -> deduction 6.0
        "condition_flags": ["scratch"], # deduction 10.0
        "inspection_damage_flags": ["dent_door"] # deduction 15.0
    })
    assert res.status_code == 200
    data = res.json()
    # 100 - (7.5 + 6.0 + 10.0 + 15.0) = 61.5
    assert data["health_score"] == 61.5
    assert data["status_summary"] == "Fair - requires attention"

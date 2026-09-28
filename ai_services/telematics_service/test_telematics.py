import pytest
from fastapi.testclient import TestClient
from ai_services.telematics_service.main import app

client = TestClient(app)

def test_safe_driving_telematics():
    data_points = [
        {"timestamp": "2026-09-28T10:00:00", "speed_mph": 45.0, "accel_g": 0.1, "latitude": 37.7749, "longitude": -122.4194},
        {"timestamp": "2026-09-28T10:00:05", "speed_mph": 50.0, "accel_g": 0.2, "latitude": 37.7750, "longitude": -122.4195}
    ]
    res = client.post("/telematics/process", json={"trip_id": 1, "data_points": data_points})
    assert res.status_code == 200
    data = res.json()
    assert data["safety_score"] == 100.0
    assert data["collision_detected"] is False
    assert data["emergency_event"] is None

def test_hard_braking_and_collision_spike():
    data_points = [
        {"timestamp": "2026-09-28T10:00:00", "speed_mph": 65.0, "accel_g": -0.6, "latitude": 37.7749, "longitude": -122.4194}, # Hard brake (-5)
        {"timestamp": "2026-09-28T10:00:02", "speed_mph": 0.0, "accel_g": -4.2, "latitude": 37.7751, "longitude": -122.4196}   # Crash spike (-40)
    ]
    res = client.post("/telematics/process", json={"trip_id": 2, "data_points": data_points})
    assert res.status_code == 200
    data = res.json()
    assert data["collision_detected"] is True
    assert data["safety_score"] == 55.0
    assert data["emergency_event"]["event_type"] == "PROBABLE_VEHICLE_COLLISION"
    assert len(data["emergency_event"]["actions_taken"]) == 3

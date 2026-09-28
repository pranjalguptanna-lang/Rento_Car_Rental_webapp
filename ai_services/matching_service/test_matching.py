import pytest
from fastapi.testclient import TestClient
from ai_services.matching_service.main import app

client = TestClient(app)


def test_nlp_matching_service():
    vehicles = [
        {
            "id": 1,
            "make": "Tesla",
            "model": "Model 3",
            "is_ev": True,
            "price_per_day": 120.0,
            "location": "San Francisco",
            "extras": ["child seat", "autopilot"],
            "description": "Smooth electric sedan"
        },
        {
            "id": 2,
            "make": "Toyota",
            "model": "Corolla",
            "is_ev": False,
            "price_per_day": 45.0,
            "location": "San Francisco",
            "extras": ["child seat"],
            "description": "Reliable budget gas car"
        },
        {
            "id": 3,
            "make": "Ford",
            "model": "F-150",
            "is_ev": False,
            "price_per_day": 90.0,
            "location": "Oakland",
            "extras": ["roof rack"],
            "description": "Heavy duty truck"
        }
    ]
    
    # Query 1: EV request with child seat
    res1 = client.post("/match", json={
        "query": "cheap EV for a weekend trip with a child seat",
        "vehicles": vehicles
    })
    assert res1.status_code == 200
    matches1 = res1.json()["matches"]
    assert len(matches1) == 3
    # Tesla (EV + child seat match) should rank top
    assert matches1[0]["vehicle_id"] == 1
    assert "EV/Electric" in matches1[0]["matched_features"]

    # Query 2: Budget car request
    res2 = client.post("/match", json={
        "query": "cheap budget car in San Francisco",
        "vehicles": vehicles
    })
    assert res2.status_code == 200
    matches2 = res2.json()["matches"]
    # Corolla ($45 budget + San Francisco location) should rank top
    assert matches2[0]["vehicle_id"] == 2
    assert "Budget-friendly price" in matches2[0]["matched_features"]

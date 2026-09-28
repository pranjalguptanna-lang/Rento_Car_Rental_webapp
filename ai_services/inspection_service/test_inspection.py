import pytest
from fastapi.testclient import TestClient
from ai_services.inspection_service.main import app

client = TestClient(app)

def test_pickup_inspection_registration():
    res = client.post("/inspection/pickup", json={
        "booking_id": 101,
        "photos": [
            {"angle": "front", "image_url_or_b64": "http://cdn.rento.com/p_front.jpg"},
            {"angle": "left_door", "image_url_or_b64": "http://cdn.rento.com/p_left.jpg"}
        ]
    })
    assert res.status_code == 200
    assert res.json()["photo_count"] == 2

def test_return_inspection_no_damage():
    photos = [
        {"angle": "front", "image_url_or_b64": "http://cdn.rento.com/p_front.jpg"},
        {"angle": "left_door", "image_url_or_b64": "http://cdn.rento.com/p_left.jpg"}
    ]
    res = client.post("/inspection/return", json={
        "booking_id": 101,
        "pickup_photos": photos,
        "return_photos": photos
    })
    assert res.status_code == 200
    report = res.json()
    assert report["has_new_damage"] is False
    assert report["total_flagged_regions"] == 0

def test_return_inspection_with_scratch_damage():
    pickup_photos = [
        {"angle": "front", "image_url_or_b64": "http://cdn.rento.com/p_front.jpg"},
        {"angle": "left_door", "image_url_or_b64": "http://cdn.rento.com/p_left.jpg"}
    ]
    return_photos = [
        {"angle": "front", "image_url_or_b64": "http://cdn.rento.com/p_front.jpg"},
        {"angle": "left_door", "image_url_or_b64": "http://cdn.rento.com/r_left_scratch.jpg"}
    ]
    res = client.post("/inspection/return", json={
        "booking_id": 101,
        "pickup_photos": pickup_photos,
        "return_photos": return_photos
    })
    assert res.status_code == 200
    report = res.json()
    assert report["has_new_damage"] is True
    assert report["total_flagged_regions"] == 1
    assert report["flags"][0]["angle"] == "left_door"

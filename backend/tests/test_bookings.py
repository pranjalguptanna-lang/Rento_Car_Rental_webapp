import pytest
import uuid
from datetime import datetime, timedelta
from fastapi.testclient import TestClient
from backend.main import app

client = TestClient(app)

def get_auth_header(email, role="renter"):
    # Register & login
    client.post("/auth/register", json={
        "email": email,
        "password": "password123",
        "role": role
    })
    res = client.post("/auth/login", data={"username": email, "password": "password123"})
    token = res.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}

def create_sample_vehicle(host_headers):
    res = client.post("/vehicles", json={
        "make": "Tesla",
        "model": "Model 3",
        "is_ev": True,
        "price_per_day": 100.0,
        "ev_details": {"battery_capacity": 75.0, "charging_type": "CCS"}
    }, headers=host_headers)
    return res.json()["id"]

def test_happy_path_booking_lifecycle():
    host_email = f"host_{uuid.uuid4().hex[:8]}@rento.com"
    renter_email = f"renter_{uuid.uuid4().hex[:8]}@rento.com"
    
    host_headers = get_auth_header(host_email, role="host")
    renter_headers = get_auth_header(renter_email, role="renter")
    
    vehicle_id = create_sample_vehicle(host_headers)
    
    start = (datetime.utcnow() + timedelta(days=1)).isoformat()
    end = (datetime.utcnow() + timedelta(days=4)).isoformat()
    
    # 1. Create booking (Default renter trust score is 95.0 + car health 100.0 -> auto-approved to confirmed)
    res = client.post("/bookings", json={
        "vehicle_id": vehicle_id,
        "start_date": start,
        "end_date": end
    }, headers=renter_headers)
    assert res.status_code == 201
    booking = res.json()
    booking_id = booking["id"]
    assert booking["status"] == "confirmed"
    assert booking["total_price"] == 300.0 # 3 days * 100.0

    # 2. Transition: Confirmed -> Pickup Inspection
    res = client.patch(f"/bookings/{booking_id}/status", json={"status": "pickup_inspection"}, headers=renter_headers)
    assert res.status_code == 200

    # 3. Transition: Pickup Inspection -> Ongoing Trip
    res = client.patch(f"/bookings/{booking_id}/status", json={"status": "ongoing_trip"}, headers=renter_headers)
    assert res.status_code == 200

    # 4. Transition: Ongoing Trip -> Return Inspection
    res = client.patch(f"/bookings/{booking_id}/status", json={"status": "return_inspection"}, headers=renter_headers)
    assert res.status_code == 200

    # 5. Transition: Return Inspection -> Completed
    res = client.patch(f"/bookings/{booking_id}/status", json={"status": "completed"}, headers=host_headers)
    assert res.status_code == 200
    assert res.json()["status"] == "completed"

def test_invalid_state_transition():
    host_email = f"host_{uuid.uuid4().hex[:8]}@rento.com"
    renter_email = f"renter_{uuid.uuid4().hex[:8]}@rento.com"
    
    host_headers = get_auth_header(host_email, role="host")
    renter_headers = get_auth_header(renter_email, role="renter")
    
    vehicle_id = create_sample_vehicle(host_headers)
    
    start = (datetime.utcnow() + timedelta(days=1)).isoformat()
    end = (datetime.utcnow() + timedelta(days=3)).isoformat()
    
    res = client.post("/bookings", json={"vehicle_id": vehicle_id, "start_date": start, "end_date": end}, headers=renter_headers)
    booking_id = res.json()["id"]
    
    # Try invalid transition: Confirmed directly to Completed
    res_bad = client.patch(f"/bookings/{booking_id}/status", json={"status": "completed"}, headers=renter_headers)
    assert res_bad.status_code == 400
    assert "Invalid state transition" in res_bad.json()["detail"]

def test_cancellation():
    host_email = f"host_{uuid.uuid4().hex[:8]}@rento.com"
    renter_email = f"renter_{uuid.uuid4().hex[:8]}@rento.com"
    
    host_headers = get_auth_header(host_email, role="host")
    renter_headers = get_auth_header(renter_email, role="renter")
    
    vehicle_id = create_sample_vehicle(host_headers)
    
    start = (datetime.utcnow() + timedelta(days=1)).isoformat()
    end = (datetime.utcnow() + timedelta(days=3)).isoformat()
    
    # Pre-pickup cancellation test
    res = client.post("/bookings", json={"vehicle_id": vehicle_id, "start_date": start, "end_date": end}, headers=renter_headers)
    booking_id = res.json()["id"]
    
    res_cancel = client.post(f"/bookings/{booking_id}/cancel", headers=renter_headers)
    assert res_cancel.status_code == 200
    assert res_cancel.json()["status"] == "cancelled"

    # Post-pickup cancellation attempt test
    res2 = client.post("/bookings", json={"vehicle_id": vehicle_id, "start_date": start, "end_date": end}, headers=renter_headers)
    booking_id2 = res2.json()["id"]
    
    # Progress to pickup inspection
    client.patch(f"/bookings/{booking_id2}/status", json={"status": "pickup_inspection"}, headers=renter_headers)

    res_cancel_fail = client.post(f"/bookings/{booking_id2}/cancel", headers=renter_headers)
    assert res_cancel_fail.status_code == 400
    assert "Cannot cancel booking once pickup inspection or trip has started" in res_cancel_fail.json()["detail"]

def test_group_booking_cost_split_and_extras():
    import json
    host_email = f"host_{uuid.uuid4().hex[:8]}@rento.com"
    renter_email = f"renter_{uuid.uuid4().hex[:8]}@rento.com"
    
    host_headers = get_auth_header(host_email, role="host")
    renter_headers = get_auth_header(renter_email, role="renter")
    
    vehicle_id = create_sample_vehicle(host_headers)
    start = (datetime.utcnow() + timedelta(days=1)).isoformat()
    end = (datetime.utcnow() + timedelta(days=3)).isoformat() # 2 days * $100 = $200

    # Extras: child_seat ($15) + wifi ($10) = $25. Total = $225.
    # 3 participants equal split = $75.0 each.
    res = client.post("/bookings", json={
        "vehicle_id": vehicle_id,
        "start_date": start,
        "end_date": end,
        "participants_count": 3,
        "bundled_extras": ["child_seat", "wifi"]
    }, headers=renter_headers)
    
    assert res.status_code == 201
    booking = res.json()
    assert booking["total_price"] == 225.0
    assert booking["participants_count"] == 3
    
    extras = json.loads(booking["bundled_extras"])
    assert "child_seat" in extras
    assert "wifi" in extras

    split_map = json.loads(booking["cost_split_details"])
    assert len(split_map) == 3
    assert split_map["Participant_1"] == 75.0
    assert split_map["Participant_2"] == 75.0
    assert split_map["Participant_3"] == 75.0



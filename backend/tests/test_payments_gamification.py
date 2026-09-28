import pytest
import uuid
from datetime import datetime, timedelta
from fastapi.testclient import TestClient
from backend.main import app

client = TestClient(app)

def get_auth_header(email, role="renter"):
    client.post("/auth/register", json={"email": email, "password": "password123", "role": role})
    res = client.post("/auth/login", data={"username": email, "password": "password123"})
    token = res.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}

def test_payment_to_notification_end_to_end_chain():
    host_email = f"host_{uuid.uuid4().hex[:8]}@rento.com"
    renter_email = f"renter_{uuid.uuid4().hex[:8]}@rento.com"

    host_headers = get_auth_header(host_email, role="host")
    renter_headers = get_auth_header(renter_email, role="renter")

    # 1. Host creates EV vehicle listing
    v_res = client.post("/vehicles", json={
        "make": "Tesla", "model": "Model 3", "is_ev": True, "price_per_day": 100.0,
        "ev_details": {"battery_capacity": 75.0, "charging_type": "CCS"}
    }, headers=host_headers)
    v_id = v_res.json()["id"]

    # 2. Renter creates booking
    start = (datetime.utcnow() + timedelta(days=1)).isoformat()
    end = (datetime.utcnow() + timedelta(days=3)).isoformat()
    b_res = client.post("/bookings", json={"vehicle_id": v_id, "start_date": start, "end_date": end}, headers=renter_headers)
    b_id = b_res.json()["id"]

    # 3. Process payment via Stripe test gateway
    p_res = client.post("/payments/process-intent", json={
        "booking_id": b_id,
        "amount": 200.0,
        "payment_method_id": "pm_card_visa"
    }, headers=renter_headers)
    assert p_res.status_code == 200
    p_data = p_res.json()
    assert p_data["status"] == "succeeded"
    payment_id = p_data["payment_id"]

    # 4. Calculate carbon eco score for EV trip (100 miles)
    c_res = client.get(f"/gamification/carbon-score?vehicle_id={v_id}&distance_miles=100")
    assert c_res.status_code == 200
    assert c_res.json()["co2_emissions_saved_kg"] > 0

    # 5. Check host reward tier calculation
    host_id = v_res.json()["host_id"]
    h_res = client.get(f"/gamification/host/{host_id}/rewards")
    assert h_res.status_code == 200
    assert h_res.json()["tier"] in ("Bronze", "Silver", "Gold")

    # 6. Verify notification dispatched to renter
    n_res = client.get("/gamification/notifications", headers=renter_headers)
    assert n_res.status_code == 200
    notifs = n_res.json()
    assert len(notifs) >= 1
    assert "Payment of $200.00 processed successfully" in notifs[0]["message"]

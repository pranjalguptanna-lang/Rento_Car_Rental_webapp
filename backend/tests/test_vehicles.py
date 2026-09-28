import io
from fastapi.testclient import TestClient
from backend.main import app

client = TestClient(app)

def test_host_vehicle_crud():
    client.post("/auth/register", json={
        "email": "testhost@rento.com",
        "password": "password123",
        "role": "host"
    })
    
    response = client.post("/auth/login", data={"username": "testhost@rento.com", "password": "password123"})
    token = response.json().get("access_token")
    headers = {"Authorization": f"Bearer {token}"}
    
    v_data = {
        "make": "Rivian",
        "model": "R1T",
        "is_ev": True,
        "price_per_day": 120.0,
        "ev_details": {
            "battery_capacity": 135.0,
            "charging_type": "CCS"
        }
    }
    resp = client.post("/vehicles", json=v_data, headers=headers)
    assert resp.status_code == 201
    vehicle_id = resp.json()["id"]
    
    s_resp = client.get("/vehicles?is_ev=true&min_price=100")
    assert s_resp.status_code == 200
    listed_vehicles = s_resp.json()
    assert any(v["id"] == vehicle_id for v in listed_vehicles)
    
    u_resp = client.put(f"/vehicles/{vehicle_id}", json={"price_per_day": 130.0}, headers=headers)
    assert u_resp.status_code == 200
    assert u_resp.json()["price_per_day"] == 130.0
    
    files = {'files': ('car.jpg', io.BytesIO(b"dummy image data"), 'image/jpeg')}
    p_resp = client.post(f"/vehicles/{vehicle_id}/photos", files=files, headers=headers)
    assert p_resp.status_code == 200
    assert "urls" in p_resp.json()

    d_resp = client.delete(f"/vehicles/{vehicle_id}", headers=headers)
    assert d_resp.status_code == 204
    
    s2_resp = client.get("/vehicles")
    deleted_vehicles = [v for v in s2_resp.json() if v["id"] == vehicle_id]
    assert len(deleted_vehicles) == 0

def test_renter_cannot_create_vehicle():
    client.post("/auth/register", json={
        "email": "testr@rento.com",
        "password": "pass",
        "role": "renter"
    })
    token = client.post("/auth/login", data={"username": "testr@rento.com", "password": "pass"}).json().get("access_token")
    headers = {"Authorization": f"Bearer {token}"}
    
    resp = client.post("/vehicles", json={
        "make": "Toyota", "model": "Camry", "is_ev": False, "price_per_day": 40.0
    }, headers=headers)
    assert resp.status_code == 403

def test_ev_range_guidance():
    # Register host & create EV vehicle (Tesla 75 kWh battery -> 75 * 3.5 = 262.5 miles range)
    import uuid
    email = f"ev_host_{uuid.uuid4().hex[:8]}@rento.com"
    client.post("/auth/register", json={"email": email, "password": "pass", "role": "host"})
    token = client.post("/auth/login", data={"username": email, "password": "pass"}).json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    v_res = client.post("/vehicles", json={
        "make": "Tesla", "model": "Model Y", "is_ev": True, "price_per_day": 100.0,
        "ev_details": {"battery_capacity": 75.0, "charging_type": "Supercharger"}
    }, headers=headers)
    v_id = v_res.json()["id"]

    # 1. Feasible trip (150 miles on 100% charge = 262.5 miles range)
    res_feasible = client.get(f"/vehicles/{v_id}/ev-guidance?trip_distance_miles=150.0&current_charge_pct=100.0")
    assert res_feasible.status_code == 200
    assert res_feasible.json()["is_trip_feasible_without_charging"] is True
    assert len(res_feasible.json()["recommended_charging_stops"]) == 0

    # 2. Infeasible trip (400 miles on 100% charge > 262.5 miles range)
    res_infeasible = client.get(f"/vehicles/{v_id}/ev-guidance?trip_distance_miles=400.0&current_charge_pct=100.0")
    assert res_infeasible.status_code == 200
    assert res_infeasible.json()["is_trip_feasible_without_charging"] is False
    assert len(res_infeasible.json()["recommended_charging_stops"]) > 0
    assert "Charging stop required" in res_infeasible.json()["guidance_message"]


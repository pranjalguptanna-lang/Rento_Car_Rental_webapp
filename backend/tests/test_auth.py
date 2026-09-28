import pytest
from fastapi.testclient import TestClient
from backend.main import app
from backend.database.database import engine, Base

client = TestClient(app)

# Note: We rely on the seed DB created in Part 2, but tests might modify it.
# In a real environment, we'd mock the DB, but since it's SQLite local, it's ok.
# For isolation, let's create a new unique renter/admin for the test.

import pytest
import uuid
from fastapi.testclient import TestClient
from backend.main import app

client = TestClient(app)

def test_register_renter():
    unique_email = f"testrenter_{uuid.uuid4().hex[:8]}@rento.com"
    response = client.post("/auth/register", json={
        "email": unique_email,
        "password": "password123",
        "role": "renter"
    })
    assert response.status_code == 201
    assert response.json()["msg"] == "User registered successfully"

def test_login_and_role_protection():
    unique_email = f"testrenter_{uuid.uuid4().hex[:8]}@rento.com"
    # Register first
    client.post("/auth/register", json={
        "email": unique_email,
        "password": "password123",
        "role": "renter"
    })
    
    # Login as renter
    response = client.post("/auth/login", data={"username": unique_email, "password": "password123"})
    assert response.status_code == 200
    token = response.json().get("access_token")
    
    headers = {"Authorization": f"Bearer {token}"}
    
    # Let's hit an endpoint that requires admin to check if renter gets forbidden
    from fastapi import Depends
    from backend.auth.dependencies import require_role
    from backend.database.models import RoleEnum
    
    @app.get("/dummy/admin-only")
    def admin_only(user = Depends(require_role(RoleEnum.admin))):
        return {"msg": "Welcome admin"}
    
    response2 = client.get("/dummy/admin-only", headers=headers)
    assert response2.status_code == 403
    assert "Requires admin role" in response2.json()["detail"]

def test_admin_access():
    unique_email = f"testadmin_{uuid.uuid4().hex[:8]}@rento.com"
    # Register admin
    client.post("/auth/register", json={
        "email": unique_email,
        "password": "password123",
        "role": "admin"
    })
    
    # Login as admin
    response = client.post("/auth/login", data={"username": unique_email, "password": "password123"})
    token = response.json().get("access_token")
    
    headers = {"Authorization": f"Bearer {token}"}
    
    response2 = client.get("/dummy/admin-only", headers=headers)
    assert response2.status_code == 200
    assert response2.json()["msg"] == "Welcome admin"


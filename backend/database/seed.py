import os
import sys

from sqlalchemy.orm import Session
from backend.database.database import SessionLocal, engine
from backend.database.models import Base, User, Hub, Vehicle, EVDetails, TrustScore, RoleEnum

def seed_db():
    print("Creating tables...")
    Base.metadata.create_all(bind=engine)
    
    db: Session = SessionLocal()

    # Clear existing
    print("Clearing old data...")
    db.query(EVDetails).delete()
    db.query(TrustScore).delete()
    db.query(Vehicle).delete()
    db.query(Hub).delete()
    db.query(User).delete()
    db.commit()

    print("Seeding Users...")
    users = [
        User(email="admin@rento.com", password_hash="hash1", role=RoleEnum.admin),
        User(email="host1@rento.com", password_hash="hash2", role=RoleEnum.host),
        User(email="host2@rento.com", password_hash="hash3", role=RoleEnum.host),
        User(email="renter1@rento.com", password_hash="hash4", role=RoleEnum.renter),
        User(email="renter2@rento.com", password_hash="hash5", role=RoleEnum.renter),
    ]
    db.add_all(users)
    db.commit()
    
    print("Seeding TrustScores...")
    for u in users:
        db.add(TrustScore(user_id=u.id, score=95.0 if u.role == RoleEnum.renter else 100.0))
    db.commit()

    print("Seeding Hubs...")
    hubs = [
        Hub(name="Downtown Hub", location="123 Main St", capacity=20),
        Hub(name="Airport Airport", location="Terminal 1", capacity=50),
    ]
    db.add_all(hubs)
    db.commit()

    print("Seeding Vehicles & EVs...")
    vehicles = [
        Vehicle(host_id=users[1].id, hub_id=hubs[0].id, make="Tesla", model="Model 3", is_ev=True, health_score=98.0, price_per_day=95.0),
        Vehicle(host_id=users[1].id, hub_id=hubs[0].id, make="Toyota", model="Camry", is_ev=False, health_score=92.0, price_per_day=45.0),
        Vehicle(host_id=users[2].id, hub_id=hubs[1].id, make="Ford", model="Mustang Mach-E", is_ev=True, health_score=95.0, price_per_day=110.0),
        Vehicle(host_id=users[2].id, hub_id=hubs[1].id, make="Honda", model="Accord", is_ev=False, health_score=85.0, price_per_day=40.0),
        Vehicle(host_id=users[2].id, hub_id=hubs[1].id, make="Nissan", model="Leaf", is_ev=True, health_score=80.0, price_per_day=60.0),
    ]
    db.add_all(vehicles)
    db.commit()
    
    # Adding EV details
    evs_details = [
        EVDetails(vehicle_id=vehicles[0].id, battery_capacity=75.0, charging_type="Tesla Supercharger"),
        EVDetails(vehicle_id=vehicles[2].id, battery_capacity=70.0, charging_type="CCS"),
        EVDetails(vehicle_id=vehicles[4].id, battery_capacity=40.0, charging_type="CHAdeMO"),
    ]
    db.add_all(evs_details)
    db.commit()

    print("Seed Complete!")
    db.close()

if __name__ == "__main__":
    seed_db()

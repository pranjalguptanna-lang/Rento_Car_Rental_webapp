from sqlalchemy import Column, Integer, String, Boolean, Float, ForeignKey, Text, Enum, DateTime
from sqlalchemy.orm import relationship
from datetime import datetime
import enum
from .database import Base

class RoleEnum(str, enum.Enum):
    renter = "renter"
    host = "host"
    admin = "admin"

class BookingStatusEnum(str, enum.Enum):
    created = "created"
    pending_approval = "pending_approval"
    confirmed = "confirmed"
    pickup_inspection = "pickup_inspection"
    ongoing_trip = "ongoing_trip"
    return_inspection = "return_inspection"
    completed = "completed"
    rejected = "rejected"
    disputed = "disputed"
    resolved = "resolved"
    cancelled = "cancelled"

class InspectionTypeEnum(str, enum.Enum):
    pickup = "pickup"
    return_ = "return"

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    password_hash = Column(String, nullable=False)
    role = Column(Enum(RoleEnum), default=RoleEnum.renter, nullable=False)
    
    trust_scores = relationship("TrustScore", back_populates="user", cascade="all, delete-orphan")
    vehicles = relationship("Vehicle", back_populates="host")
    bookings = relationship("Booking", back_populates="renter")
    reviews = relationship("Review", back_populates="reviewer")
    notifications = relationship("Notification", back_populates="user")

class TrustScore(Base):
    __tablename__ = "trust_scores"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    score = Column(Float, default=100.0)
    
    user = relationship("User", back_populates="trust_scores")

class Hub(Base):
    __tablename__ = "hubs"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    location = Column(String, nullable=False)
    capacity = Column(Integer, default=10)

    vehicles = relationship("Vehicle", back_populates="hub")

class Vehicle(Base):
    __tablename__ = "vehicles"
    id = Column(Integer, primary_key=True, index=True)
    host_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    hub_id = Column(Integer, ForeignKey("hubs.id"), nullable=True)
    make = Column(String, nullable=False)
    model = Column(String, nullable=False)
    is_ev = Column(Boolean, default=False)
    is_active = Column(Boolean, default=True)
    health_score = Column(Float, default=100.0)
    price_per_day = Column(Float, nullable=False)

    host = relationship("User", back_populates="vehicles")
    hub = relationship("Hub", back_populates="vehicles")
    ev_details = relationship("EVDetails", back_populates="vehicle", uselist=False, cascade="all, delete-orphan")
    bookings = relationship("Booking", back_populates="vehicle")

class EVDetails(Base):
    __tablename__ = "ev_details"
    id = Column(Integer, primary_key=True, index=True)
    vehicle_id = Column(Integer, ForeignKey("vehicles.id"), unique=True, nullable=False)
    battery_capacity = Column(Float, nullable=False) # in kWh
    charging_type = Column(String, nullable=False)

    vehicle = relationship("Vehicle", back_populates="ev_details")

class Payment(Base):
    __tablename__ = "payments"
    id = Column(Integer, primary_key=True, index=True)
    amount = Column(Float, nullable=False)
    status = Column(String, default="pending")

    booking = relationship("Booking", back_populates="payment", uselist=False)

class Inspection(Base):
    __tablename__ = "inspections"
    id = Column(Integer, primary_key=True, index=True)
    type = Column(Enum(InspectionTypeEnum), nullable=False)
    photo_urls = Column(Text, nullable=True)
    flags = Column(Text, nullable=True)

class Trip(Base):
    __tablename__ = "trips"
    id = Column(Integer, primary_key=True, index=True)
    telematics_log = Column(Text, nullable=True)
    safety_score = Column(Float, nullable=True)
    
    booking = relationship("Booking", back_populates="trip", uselist=False)

class Review(Base):
    __tablename__ = "reviews"
    id = Column(Integer, primary_key=True, index=True)
    reviewer_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    rating = Column(Integer, nullable=False)
    comment = Column(Text, nullable=True)
    
    reviewer = relationship("User", back_populates="reviews")

class Booking(Base):
    __tablename__ = "bookings"
    id = Column(Integer, primary_key=True, index=True)
    renter_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    vehicle_id = Column(Integer, ForeignKey("vehicles.id"), nullable=False)
    payment_id = Column(Integer, ForeignKey("payments.id"), nullable=True)
    pickup_inspection_id = Column(Integer, ForeignKey("inspections.id"), nullable=True)
    return_inspection_id = Column(Integer, ForeignKey("inspections.id"), nullable=True)
    trip_id = Column(Integer, ForeignKey("trips.id"), nullable=True)
    review_id = Column(Integer, ForeignKey("reviews.id"), nullable=True)
    start_date = Column(DateTime, nullable=False)
    end_date = Column(DateTime, nullable=False)
    total_price = Column(Float, nullable=False, default=0.0)
    deposit_amount = Column(Float, nullable=False, default=0.0)
    status = Column(Enum(BookingStatusEnum), default=BookingStatusEnum.created, nullable=False)
    participants_count = Column(Integer, default=1, nullable=False)
    bundled_extras = Column(Text, nullable=True) # JSON list string e.g. ["child_seat", "wifi"]
    cost_split_details = Column(Text, nullable=True) # JSON details of per-participant cost split


    
    renter = relationship("User", back_populates="bookings")
    vehicle = relationship("Vehicle", back_populates="bookings")
    payment = relationship("Payment", back_populates="booking")
    trip = relationship("Trip", back_populates="booking")
    pickup_inspection = relationship("Inspection", foreign_keys=[pickup_inspection_id])
    return_inspection = relationship("Inspection", foreign_keys=[return_inspection_id])
    review = relationship("Review")


class Notification(Base):
    __tablename__ = "notifications"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    message = Column(String, nullable=False)
    is_read = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", back_populates="notifications")

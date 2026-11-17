from datetime import datetime
from uuid import uuid4

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Index, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

try:
    from .clock import utc_now
    from .database import Base
except ImportError:
    from clock import utc_now
    from database import Base


def new_id() -> str:
    return str(uuid4())


class User(Base):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    username: Mapped[str] = mapped_column(String(120), unique=True, index=True)
    display_name: Mapped[str] = mapped_column(String(120))
    role: Mapped[str] = mapped_column(String(20), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now)


class DemoSession(Base):
    __tablename__ = "sessions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    token_digest: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime, index=True)


class Location(Base):
    __tablename__ = "locations"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    name: Mapped[str] = mapped_column(String(160))
    neighborhood: Mapped[str] = mapped_column(String(120))
    latitude: Mapped[float] = mapped_column(Float)
    longitude: Mapped[float] = mapped_column(Float)
    area_density: Mapped[float] = mapped_column(Float, default=0.5)
    bin_capacity_kg: Mapped[float] = mapped_column(Float, default=120)
    days_since_pickup: Mapped[int] = mapped_column(Integer, default=1)
    last_collected_kg: Mapped[float] = mapped_column(Float, default=0)
    predicted_fill_percent: Mapped[float] = mapped_column(Float, default=0)
    predicted_waste_kg: Mapped[float] = mapped_column(Float, default=0)
    available: Mapped[bool] = mapped_column(Boolean, default=True)


class Vehicle(Base):
    __tablename__ = "vehicles"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    name: Mapped[str] = mapped_column(String(120))
    vehicle_type: Mapped[str] = mapped_column(String(100))
    capacity_kg: Mapped[float] = mapped_column(Float)
    average_speed_kmh: Mapped[float] = mapped_column(Float, default=25)
    available: Mapped[bool] = mapped_column(Boolean, default=True)
    driver_id: Mapped[str | None] = mapped_column(ForeignKey("users.id"), nullable=True, index=True)
    current_latitude: Mapped[float] = mapped_column(Float)
    current_longitude: Mapped[float] = mapped_column(Float)


class Route(Base):
    __tablename__ = "routes"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    vehicle_id: Mapped[str] = mapped_column(ForeignKey("vehicles.id"), index=True)
    driver_id: Mapped[str] = mapped_column(ForeignKey("users.id"), index=True)
    status: Mapped[str] = mapped_column(String(24), default="planned", index=True)
    distance_km: Mapped[float] = mapped_column(Float, default=0)
    duration_minutes: Mapped[float] = mapped_column(Float, default=0)
    current_waypoint_index: Mapped[int] = mapped_column(Integer, default=0)
    speed_multiplier: Mapped[float] = mapped_column(Float, default=1)
    current_latitude: Mapped[float] = mapped_column(Float)
    current_longitude: Mapped[float] = mapped_column(Float)
    ai_route_notes: Mapped[str] = mapped_column(Text, default="")
    ai_notes_source: Mapped[str] = mapped_column(String(32), default="local_rules")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now)
    started_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)


class Report(Base):
    __tablename__ = "reports"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    citizen_id: Mapped[str] = mapped_column(ForeignKey("users.id"), index=True)
    description: Mapped[str] = mapped_column(Text)
    address: Mapped[str] = mapped_column(String(240), default="")
    latitude: Mapped[float] = mapped_column(Float)
    longitude: Mapped[float] = mapped_column(Float)
    urgency: Mapped[str] = mapped_column(String(16), default="medium", index=True)
    waste_type: Mapped[str] = mapped_column(String(24), default="General")
    priority_score: Mapped[int] = mapped_column(Integer, default=40)
    estimated_waste_kg: Mapped[float] = mapped_column(Float, default=20)
    handling_instructions: Mapped[str] = mapped_column(Text, default="")
    triage_source: Mapped[str] = mapped_column(String(32), default="rules_fallback")
    triage_warning: Mapped[str] = mapped_column(Text, default="")
    status: Mapped[str] = mapped_column(String(24), default="Pending", index=True)
    assigned_route_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    eta: Mapped[str | None] = mapped_column(String(32), nullable=True)
    photo_path: Mapped[str | None] = mapped_column(String(240), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now, index=True)


class RouteStop(Base):
    __tablename__ = "route_stops"
    __table_args__ = (
        UniqueConstraint("route_id", "sequence_number", name="uq_route_stop_sequence"),
        Index("ix_route_stop_route_status", "route_id", "status"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    route_id: Mapped[str] = mapped_column(ForeignKey("routes.id", ondelete="CASCADE"), index=True)
    sequence_number: Mapped[int] = mapped_column(Integer)
    location_id: Mapped[str | None] = mapped_column(ForeignKey("locations.id"), nullable=True)
    report_id: Mapped[str | None] = mapped_column(ForeignKey("reports.id"), nullable=True)
    name: Mapped[str] = mapped_column(String(160))
    latitude: Mapped[float] = mapped_column(Float)
    longitude: Mapped[float] = mapped_column(Float)
    waste_kg: Mapped[float] = mapped_column(Float)
    eta: Mapped[str] = mapped_column(String(32))
    status: Mapped[str] = mapped_column(String(24), default="Pending", index=True)


class CollectionRecord(Base):
    __tablename__ = "collection_records"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    location_id: Mapped[str] = mapped_column(ForeignKey("locations.id"), index=True)
    collected_kg: Mapped[float] = mapped_column(Float)
    day_of_week: Mapped[int] = mapped_column(Integer)
    rainfall_mm: Mapped[float] = mapped_column(Float, default=0)
    collected_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now, index=True)


class SimulationEvent(Base):
    __tablename__ = "simulation_events"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    route_id: Mapped[str] = mapped_column(ForeignKey("routes.id", ondelete="CASCADE"), index=True)
    event_type: Mapped[str] = mapped_column(String(32))
    latitude: Mapped[float] = mapped_column(Float)
    longitude: Mapped[float] = mapped_column(Float)
    details: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now, index=True)

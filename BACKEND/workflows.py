from __future__ import annotations

import asyncio
import hashlib
import logging
import mimetypes
import os
from datetime import timedelta
from pathlib import Path
from typing import Any
from uuid import uuid4

from fastapi import APIRouter, Depends, File, Form, Header, HTTPException, UploadFile
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from starlette.concurrency import run_in_threadpool

try:
    from . import llm_service, ml_model
    from .auth import create_demo_session, get_current_user, require_roles
    from .clock import utc_now
    from .database import get_db
    from .engine import haversine_km
    from .models import (
        CollectionRecord,
        DemoSession,
        Location,
        Report,
        Route,
        RouteStop,
        SimulationEvent,
        User,
        Vehicle,
    )
    from .schemas import (
        DemoLoginRequest,
        DriverPosition,
        ReportAssignment,
        SimulationSpeed,
        TriageRequest,
        VehiclePatch,
    )
    from .settings import DEPOT, DISPOSAL_SITE, UPLOAD_DIR
except ImportError:
    import llm_service
    import ml_model
    from auth import create_demo_session, get_current_user, require_roles
    from clock import utc_now
    from database import get_db
    from engine import haversine_km
    from models import CollectionRecord, DemoSession, Location, Report, Route, RouteStop, SimulationEvent, User, Vehicle
    from schemas import DemoLoginRequest, DriverPosition, ReportAssignment, SimulationSpeed, TriageRequest, VehiclePatch
    from settings import DEPOT, DISPOSAL_SITE, UPLOAD_DIR


LOGGER = logging.getLogger("buildx.workflows")
router = APIRouter(prefix="/api/v1")
admin_only = require_roles("admin")
citizen_only = require_roles("citizen")
driver_only = require_roles("driver")
authenticated = require_roles("admin", "driver", "citizen")
MAX_PHOTO_BYTES = 5 * 1024 * 1024
IMAGE_SIGNATURES = {
    "image/jpeg": (b"\xff\xd8\xff",),
    "image/png": (b"\x89PNG\r\n\x1a\n",),
    "image/webp": (b"RIFF",),
    "image/gif": (b"GIF87a", b"GIF89a"),
}
ROAD_DISTANCE_FACTOR = 1.3
SERVICE_MINUTES_PER_STOP = 8


def _user_view(user: User) -> dict[str, str]:
    return {
        "id": user.id,
        "username": user.username,
        "displayName": user.display_name,
        "role": user.role,
    }


def _report_view(db: Session, report: Report) -> dict[str, Any]:
    citizen = db.get(User, report.citizen_id)
    return {
        "id": report.id,
        "citizenId": report.citizen_id,
        "citizenName": citizen.display_name if citizen else "Unknown citizen",
        "description": report.description,
        "address": report.address,
        "latitude": report.latitude,
        "longitude": report.longitude,
        "urgency": report.urgency,
        "wasteType": report.waste_type,
        "priorityScore": report.priority_score,
        "estimatedWasteKg": report.estimated_waste_kg,
        "handlingInstructions": report.handling_instructions,
        "triageSource": report.triage_source,
        "triageWarning": report.triage_warning,
        "status": report.status,
        "assignedRouteId": report.assigned_route_id,
        "eta": report.eta,
        "photoUrl": f"/api/v1/uploads/{report.photo_path}" if report.photo_path else None,
        "createdAt": report.created_at.isoformat(),
    }


def _vehicle_view(db: Session, vehicle: Vehicle) -> dict[str, Any]:
    driver = db.get(User, vehicle.driver_id) if vehicle.driver_id else None
    return {
        "id": vehicle.id,
        "name": vehicle.name,
        "type": vehicle.vehicle_type,
        "capacityKg": vehicle.capacity_kg,
        "averageSpeedKmh": vehicle.average_speed_kmh,
        "available": vehicle.available,
        "driverId": vehicle.driver_id,
        "driverName": driver.display_name if driver else None,
        "latitude": vehicle.current_latitude,
        "longitude": vehicle.current_longitude,
    }


def _location_prediction(location: Location) -> dict[str, Any]:
    predicted = ml_model.predict_fill_level(
        area_density=location.area_density,
        days_since_pickup=location.days_since_pickup,
        rainfall_mm=0,
        bin_capacity_kg=location.bin_capacity_kg,
    )
    location.predicted_fill_percent = predicted["fillLevelPercent"]
    location.predicted_waste_kg = predicted["estimatedWasteKg"]
    return {
        "id": location.id,
        "name": location.name,
        "neighborhood": location.neighborhood,
        "latitude": location.latitude,
        "longitude": location.longitude,
        "areaDensity": location.area_density,
        "binCapacityKg": location.bin_capacity_kg,
        "daysSincePickup": location.days_since_pickup,
        "lastCollectedKg": location.last_collected_kg,
        "available": location.available,
        **predicted,
    }


def _route_stops(db: Session, route: Route) -> list[dict[str, Any]]:
    stops = db.query(RouteStop).filter(RouteStop.route_id == route.id).order_by(RouteStop.sequence_number).all()
    result: list[dict[str, Any]] = []
    for stop in stops:
        report = db.get(Report, stop.report_id) if stop.report_id else None
        location = db.get(Location, stop.location_id) if stop.location_id else None
        result.append({
            "id": stop.id,
            "sequenceNumber": stop.sequence_number,
            "locationId": stop.location_id,
            "reportId": stop.report_id,
            "name": stop.name,
            "latitude": stop.latitude,
            "longitude": stop.longitude,
            "wasteKg": stop.waste_kg,
            "eta": stop.eta,
            "status": stop.status,
            "wasteType": report.waste_type if report else "General",
            "urgency": report.urgency if report else "medium",
            "description": report.description if report else "",
            "address": (report.address or location.neighborhood) if report else (location.neighborhood if location else ""),
        })
    return result


def _route_view(db: Session, route: Route) -> dict[str, Any]:
    vehicle = db.get(Vehicle, route.vehicle_id)
    stops = _route_stops(db, route)
    load_used = round(sum(stop["wasteKg"] for stop in stops), 1)
    load_capacity = vehicle.capacity_kg if vehicle else 0
    waypoints = [{
        "type": "depot",
        "name": DEPOT["name"],
        "latitude": DEPOT["latitude"],
        "longitude": DEPOT["longitude"],
    }]
    waypoints.extend({
        "type": "stop",
        "sequenceNumber": stop["sequenceNumber"],
        "name": stop["name"],
        "latitude": stop["latitude"],
        "longitude": stop["longitude"],
    } for stop in stops)
    waypoints.append({
        "type": "disposal",
        "name": DISPOSAL_SITE["name"],
        "latitude": DISPOSAL_SITE["latitude"],
        "longitude": DISPOSAL_SITE["longitude"],
    })
    return {
        "id": route.id,
        "vehicleId": route.vehicle_id,
        "vehicleName": vehicle.name if vehicle else "Unknown vehicle",
        "driverId": route.driver_id,
        "status": route.status,
        "distanceKm": route.distance_km,
        "durationMinutes": route.duration_minutes,
        "loadUsedKg": load_used,
        "loadCapacityKg": load_capacity,
        "utilizationPercent": round(load_used / load_capacity * 100, 1) if load_capacity else 0,
        "currentWaypointIndex": route.current_waypoint_index,
        "speedMultiplier": route.speed_multiplier,
        "currentPosition": {
            "latitude": route.current_latitude,
            "longitude": route.current_longitude,
        },
        "aiRouteNotes": route.ai_route_notes,
        "aiNotesSource": route.ai_notes_source,
        "createdAt": route.created_at.isoformat(),
        "startedAt": route.started_at.isoformat() if route.started_at else None,
        "completedAt": route.completed_at.isoformat() if route.completed_at else None,
        "stops": stops,
        "waypoints": waypoints,
    }


def _owned_driver_route(db: Session, user: User) -> Route:
    route = (
        db.query(Route)
        .filter(Route.driver_id == user.id, Route.status.in_(("planned", "active", "paused")))
        .order_by((Route.status == "active").desc(), Route.created_at.desc())
        .first()
    )
    if route is None:
        raise HTTPException(status_code=404, detail="No planned or active route is assigned to this driver.")
    return route


def _event(db: Session, route: Route, event_type: str, details: str = "") -> None:
    db.add(SimulationEvent(
        route_id=route.id,
        event_type=event_type,
        latitude=route.current_latitude,
        longitude=route.current_longitude,
        details=details,
    ))


def _refresh_route_etas(db: Session, route: Route) -> None:
    vehicle = db.get(Vehicle, route.vehicle_id)
    speed = max(vehicle.average_speed_kmh if vehicle else 24, 1)
    now = utc_now()
    elapsed_minutes = 0.0
    previous = {"latitude": route.current_latitude, "longitude": route.current_longitude}
    stops = (
        db.query(RouteStop)
        .filter(RouteStop.route_id == route.id, RouteStop.status != "Collected")
        .order_by(RouteStop.sequence_number)
        .all()
    )
    for stop in stops:
        point = {"latitude": stop.latitude, "longitude": stop.longitude}
        elapsed_minutes += haversine_km(previous, point) / speed * 60
        arrival = now + timedelta(minutes=elapsed_minutes)
        stop.eta = arrival.strftime("%H:%M")
        if stop.report_id:
            report = db.get(Report, stop.report_id)
            if report:
                report.eta = arrival.isoformat()
        elapsed_minutes += 8
        previous = point


def _minutes_after_shift_start(elapsed_minutes: float) -> str:
    total_minutes = 8 * 60 + round(elapsed_minutes)
    day_offset, minute_of_day = divmod(total_minutes, 24 * 60)
    time_label = f"{minute_of_day // 60:02d}:{minute_of_day % 60:02d}"
    return f"{time_label} (+{day_offset}d)" if day_offset else time_label


def _report_insertion_index(
    stops: list[RouteStop],
    latitude: float,
    longitude: float,
    start_point: dict[str, float],
) -> int:
    point = {"latitude": latitude, "longitude": longitude}
    best_index = 0
    best_added_distance = float("inf")
    for index in range(len(stops) + 1):
        previous = start_point if index == 0 else {
            "latitude": stops[index - 1].latitude,
            "longitude": stops[index - 1].longitude,
        }
        following = DISPOSAL_SITE if index == len(stops) else {
            "latitude": stops[index].latitude,
            "longitude": stops[index].longitude,
        }
        added_distance = (
            haversine_km(previous, point)
            + haversine_km(point, following)
            - haversine_km(previous, following)
        )
        if added_distance < best_added_distance:
            best_index = index
            best_added_distance = added_distance
    return best_index


def _schedule_planned_route(db: Session, route: Route) -> None:
    vehicle = db.get(Vehicle, route.vehicle_id)
    speed = max(vehicle.average_speed_kmh if vehicle else 24, 1)
    stops = db.query(RouteStop).filter(
        RouteStop.route_id == route.id,
    ).order_by(RouteStop.sequence_number).all()
    previous = {"latitude": route.current_latitude, "longitude": route.current_longitude}
    elapsed_minutes = 0.0
    route_distance = 0.0
    for stop in stops:
        point = {"latitude": stop.latitude, "longitude": stop.longitude}
        leg_distance = haversine_km(previous, point) * ROAD_DISTANCE_FACTOR
        route_distance += leg_distance
        elapsed_minutes += leg_distance / ROAD_DISTANCE_FACTOR / speed * 60
        stop.eta = _minutes_after_shift_start(elapsed_minutes)
        if stop.report_id:
            report = db.get(Report, stop.report_id)
            if report:
                report.eta = stop.eta
        elapsed_minutes += SERVICE_MINUTES_PER_STOP
        previous = point
    final_leg = haversine_km(previous, DISPOSAL_SITE) * ROAD_DISTANCE_FACTOR
    route.distance_km = round(route_distance + final_leg, 3)
    route.duration_minutes = round(elapsed_minutes + final_leg / ROAD_DISTANCE_FACTOR / speed * 60, 1)


@router.post("/auth/demo-login")
def demo_login(payload: DemoLoginRequest, db: Session = Depends(get_db)) -> dict[str, Any]:
    token, user = create_demo_session(db, payload.username.strip().lower())
    return {"accessToken": token, "tokenType": "bearer", "user": _user_view(user), "demoOnly": True}


@router.get("/auth/me")
def current_session(user: User = Depends(authenticated)) -> dict[str, Any]:
    return {"user": _user_view(user), "demoOnly": True}


@router.post("/auth/logout")
def logout(
    authorization: str | None = Header(default=None),
    user: User = Depends(authenticated),
    db: Session = Depends(get_db),
) -> dict[str, bool]:
    if authorization and authorization.startswith("Bearer "):
        digest = hashlib.sha256(authorization.removeprefix("Bearer ").strip().encode("utf-8")).hexdigest()
        db.query(DemoSession).filter(
            DemoSession.token_digest == digest,
            DemoSession.user_id == user.id,
        ).delete()
        db.commit()
    return {"success": True}


@router.get("/locations")
def list_locations(
    db: Session = Depends(get_db),
    _: User = Depends(authenticated),
) -> dict[str, Any]:
    locations = db.query(Location).order_by(Location.name).all()
    try:
        data = [_location_prediction(location) for location in locations]
    except (OSError, KeyError, ValueError) as exc:
        LOGGER.exception("Demand predictions could not be calculated.")
        raise HTTPException(status_code=503, detail="Demand prediction model is unavailable.") from exc
    db.commit()
    return {"locations": data, "modelVersion": data[0]["modelVersion"] if data else None}


@router.get("/vehicles")
def list_vehicles(db: Session = Depends(get_db), _: User = Depends(authenticated)) -> dict[str, Any]:
    vehicles = db.query(Vehicle).order_by(Vehicle.capacity_kg).all()
    return {"vehicles": [_vehicle_view(db, vehicle) for vehicle in vehicles]}


@router.get("/ml/status")
def ml_status(_: User = Depends(authenticated)) -> dict[str, Any]:
    return {"available": True, "modelVersion": ml_model.MODEL_VERSION, "modelType": "RandomForestRegressor"}


@router.get("/llm/status")
def get_llm_status(_: User = Depends(authenticated)) -> dict[str, Any]:
    return llm_service.llm_status()


@router.post("/llm/triage")
async def triage_report(
    payload: TriageRequest,
    _: User = Depends(authenticated),
) -> dict[str, Any]:
    return await run_in_threadpool(llm_service.triage_citizen_report, payload.description, payload.urgency)


@router.post("/citizen/reports")
async def create_citizen_report(
    description: str = Form(min_length=5, max_length=2000),
    latitude: float = Form(ge=-90, le=90),
    longitude: float = Form(ge=-180, le=180),
    address: str = Form(default="", max_length=240),
    urgency: str = Form(default="medium", pattern="^(low|medium|high)$"),
    photo: UploadFile | None = File(default=None),
    user: User = Depends(citizen_only),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    photo_path: str | None = None
    if photo is not None:
        content_type = (photo.content_type or "").lower()
        signature_options = IMAGE_SIGNATURES.get(content_type)
        if signature_options is None:
            raise HTTPException(status_code=415, detail="Upload a JPEG, PNG, WebP, or GIF image.")
        contents = await photo.read(MAX_PHOTO_BYTES + 1)
        if len(contents) > MAX_PHOTO_BYTES:
            raise HTTPException(status_code=413, detail="The image must be 5 MB or smaller.")
        if not any(contents.startswith(signature) for signature in signature_options):
            raise HTTPException(status_code=415, detail="The uploaded file does not match its declared image type.")
        if content_type == "image/webp" and contents[8:12] != b"WEBP":
            raise HTTPException(status_code=415, detail="The uploaded file is not a valid WebP image.")
        extension = mimetypes.guess_extension(content_type) or ".img"
        photo_path = f"{uuid4().hex}{extension}"
        try:
            (UPLOAD_DIR / photo_path).write_bytes(contents)
        except OSError as exc:
            LOGGER.exception("Unable to store citizen report image.")
            raise HTTPException(status_code=500, detail="Image upload could not be stored.") from exc

    triage = await run_in_threadpool(llm_service.triage_citizen_report, description, urgency)
    report = Report(
        citizen_id=user.id,
        description=description.strip(),
        address=address.strip(),
        latitude=latitude,
        longitude=longitude,
        urgency=triage["urgency"],
        waste_type=triage["wasteType"],
        priority_score=triage["priorityScore"],
        estimated_waste_kg=triage["estimatedWasteKg"],
        handling_instructions=triage["handlingInstructions"],
        triage_source=triage["source"],
        triage_warning=triage["warning"],
        photo_path=photo_path,
    )
    db.add(report)
    db.commit()
    db.refresh(report)
    return _report_view(db, report)


@router.get("/citizen/reports")
def list_citizen_reports(
    user: User = Depends(citizen_only),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    reports = (
        db.query(Report)
        .filter(Report.citizen_id == user.id)
        .order_by(Report.created_at.desc())
        .all()
    )
    return {"reports": [_report_view(db, report) for report in reports]}


@router.get("/admin/reports")
def list_all_reports(
    db: Session = Depends(get_db),
    _: User = Depends(admin_only),
) -> dict[str, Any]:
    reports = db.query(Report).order_by(Report.created_at.desc()).all()
    return {"reports": [_report_view(db, report) for report in reports]}


@router.get("/admin/overview")
def admin_overview(
    db: Session = Depends(get_db),
    _: User = Depends(admin_only),
) -> dict[str, Any]:
    reports = db.query(Report).order_by(Report.created_at.desc()).all()
    vehicles = db.query(Vehicle).order_by(Vehicle.capacity_kg).all()
    routes = db.query(Route).order_by(Route.created_at.desc()).limit(12).all()
    locations = db.query(Location).order_by(Location.name).all()
    try:
        location_data = [_location_prediction(location) for location in locations]
    except (OSError, KeyError, ValueError) as exc:
        LOGGER.exception("Demand predictions could not be calculated for the admin dashboard.")
        raise HTTPException(status_code=503, detail="Demand prediction model is unavailable.") from exc
    db.commit()
    return {
        "metrics": {
            "pendingReports": sum(report.status == "Pending" for report in reports),
            "assignedReports": sum(report.status == "Assigned" for report in reports),
            "enRouteReports": sum(report.status == "En Route" for report in reports),
            "collectedReports": sum(report.status == "Collected" for report in reports),
            "activeRoutes": db.query(Route).filter(Route.status == "active").count(),
            "unavailableVehicles": sum(not vehicle.available for vehicle in vehicles),
            "averagePredictedFillPercent": round(
                sum(item["fillLevelPercent"] for item in location_data) / len(location_data), 1
            ) if location_data else 0,
        },
        "reports": [_report_view(db, report) for report in reports],
        "vehicles": [_vehicle_view(db, vehicle) for vehicle in vehicles],
        "routes": [_route_view(db, route) for route in routes],
        "locations": location_data,
        "llm": llm_service.llm_status(),
    }


@router.patch("/admin/vehicles/{vehicle_id}")
def update_vehicle_availability(
    vehicle_id: str,
    payload: VehiclePatch,
    db: Session = Depends(get_db),
    _: User = Depends(admin_only),
) -> dict[str, Any]:
    vehicle = db.get(Vehicle, vehicle_id)
    if vehicle is None:
        raise HTTPException(status_code=404, detail="Vehicle not found.")
    active_route = db.query(Route).filter(
        Route.vehicle_id == vehicle.id,
        Route.status == "active",
    ).first()
    if active_route and payload.available:
        raise HTTPException(status_code=409, detail="A truck on an active route cannot be marked available.")
    vehicle.available = payload.available
    db.commit()
    return _vehicle_view(db, vehicle)


@router.post("/admin/reports/{report_id}/assign")
async def assign_report_to_driver(
    report_id: str,
    payload: ReportAssignment,
    db: Session = Depends(get_db),
    _: User = Depends(admin_only),
) -> dict[str, Any]:
    report = db.get(Report, report_id)
    if report is None:
        raise HTTPException(status_code=404, detail="Citizen report not found.")
    if report.status != "Pending":
        raise HTTPException(status_code=409, detail="Only pending reports can be assigned.")
    vehicle = db.get(Vehicle, payload.vehicleId)
    if vehicle is None:
        raise HTTPException(status_code=404, detail="Vehicle not found.")
    if vehicle.driver_id is None:
        raise HTTPException(status_code=409, detail="This vehicle does not have an assigned driver.")
    if not vehicle.available:
        raise HTTPException(status_code=409, detail="This vehicle is unavailable.")
    occupied_route = db.query(Route).filter(
        Route.vehicle_id == vehicle.id,
        Route.status.in_(("active", "paused")),
    ).first()
    if occupied_route:
        raise HTTPException(status_code=409, detail="A driver on an active or paused route cannot receive a new stop.")
    if report.estimated_waste_kg > vehicle.capacity_kg:
        raise HTTPException(
            status_code=409,
            detail=f"The report's {report.estimated_waste_kg:g} kg load exceeds this truck's {vehicle.capacity_kg:g} kg capacity.",
        )

    route = (
        db.query(Route)
        .filter(Route.vehicle_id == vehicle.id, Route.status == "planned")
        .order_by(Route.created_at.desc())
        .first()
    )
    existing_stops = (
        db.query(RouteStop)
        .filter(RouteStop.route_id == route.id)
        .order_by(RouteStop.sequence_number)
        .all()
        if route
        else []
    )
    current_load = sum(stop.waste_kg for stop in existing_stops)
    if current_load + report.estimated_waste_kg > vehicle.capacity_kg + 1e-9:
        remaining_capacity = max(0, vehicle.capacity_kg - current_load)
        raise HTTPException(
            status_code=409,
            detail=(
                f"{vehicle.name} has {remaining_capacity:g} kg of remaining capacity, "
                f"but this report needs {report.estimated_waste_kg:g} kg."
            ),
        )

    if route is None:
        route = Route(
            vehicle_id=vehicle.id,
            driver_id=vehicle.driver_id,
            status="planned",
            current_waypoint_index=0,
            speed_multiplier=1,
            current_latitude=vehicle.current_latitude,
            current_longitude=vehicle.current_longitude,
        )
        db.add(route)
        db.flush()
        insertion_index = 0
    else:
        insertion_index = _report_insertion_index(
            existing_stops,
            report.latitude,
            report.longitude,
            {"latitude": route.current_latitude, "longitude": route.current_longitude},
        )
        for index, stop in enumerate(existing_stops, start=1):
            stop.sequence_number = -index
        db.flush()

    new_stop = RouteStop(
        route_id=route.id,
        sequence_number=-(len(existing_stops) + 1) if existing_stops else 1,
        report_id=report.id,
        name=report.address.strip() or f"Citizen report {report.id[:8]}",
        latitude=report.latitude,
        longitude=report.longitude,
        waste_kg=report.estimated_waste_kg,
        eta="08:00",
        status="Pending",
    )
    db.add(new_stop)
    db.flush()

    ordered_stops = [
        *existing_stops[:insertion_index],
        new_stop,
        *existing_stops[insertion_index:],
    ]
    for sequence_number, stop in enumerate(ordered_stops, start=1):
        stop.sequence_number = sequence_number
    db.flush()
    _schedule_planned_route(db, route)
    report.status = "Assigned"
    report.assigned_route_id = route.id
    report.eta = new_stop.eta
    route_notes = await run_in_threadpool(llm_service.generate_driver_notes, _route_stops(db, route))
    route.ai_route_notes = route_notes["text"]
    route.ai_notes_source = route_notes["source"]
    _event(db, route, "report_assigned", report.id)
    db.commit()
    return {"route": _route_view(db, route), "report": _report_view(db, report)}


@router.post("/admin/dispatch")
async def optimize_and_dispatch(
    db: Session = Depends(get_db),
    _: User = Depends(admin_only),
) -> dict[str, Any]:
    try:
        from .engine import run_engine
    except ImportError:
        from engine import run_engine

    locations = db.query(Location).order_by(Location.name).all()
    vehicles = db.query(Vehicle).order_by(Vehicle.capacity_kg.desc()).all()
    pending_reports = db.query(Report).filter(Report.status == "Pending").all()
    if len(vehicles) < 3 or len({vehicle.capacity_kg for vehicle in vehicles}) < 3:
        raise HTTPException(status_code=409, detail="Dispatch needs at least three vehicles with different capacities.")
    try:
        nodes: list[dict[str, Any]] = []
        node_targets: dict[str, tuple[str, Any]] = {}
        for location in locations:
            prediction = _location_prediction(location)
            fill = prediction["fillLevelPercent"]
            priority = 5 if fill >= 85 else 4 if fill >= 70 else 3 if fill >= 50 else 2
            node_id = f"location:{location.id}"
            attributes = ["overflowing"] if fill >= 90 else ["high_priority"] if priority >= 4 else []
            nodes.append({
                "id": node_id,
                "name": location.name,
                "latitude": location.latitude,
                "longitude": location.longitude,
                "wasteKg": prediction["estimatedWasteKg"],
                "priority": priority,
                "attributes": attributes,
                "available": location.available,
                "disrupted": False,
            })
            node_targets[node_id] = ("location", location)
        for report in pending_reports:
            priority = max(1, min(5, (report.priority_score + 19) // 20))
            node_id = f"report:{report.id}"
            nodes.append({
                "id": node_id,
                "name": report.address.strip() or f"Citizen report {report.id[:8]}",
                "latitude": report.latitude,
                "longitude": report.longitude,
                "wasteKg": report.estimated_waste_kg,
                "priority": priority,
                "attributes": ["high_priority"] if priority >= 4 else [],
                "available": True,
                "disrupted": False,
            })
            node_targets[node_id] = ("report", report)
        engine_input = {
            "scenarioId": f"dispatch-{utc_now().strftime('%Y%m%d%H%M%S')}",
            "userPriority": "urgent",
            "parameters": {
                "allowDisruptions": True,
                "shiftStart": "08:00",
                "serviceMinutesPerStop": 8,
                "averageSpeedKmh": 24,
                "roadDistanceFactor": 1.3,
            },
            "depot": DEPOT,
            "vehicles": [{
                "id": vehicle.id,
                "name": vehicle.name,
                "type": vehicle.vehicle_type,
                "capacityKg": vehicle.capacity_kg,
                "available": vehicle.available,
                "averageSpeedKmh": vehicle.average_speed_kmh,
            } for vehicle in vehicles],
            "nodes": nodes,
        }
        result = await run_in_threadpool(run_engine, engine_input)
        if result.get("status") != "success":
            raise HTTPException(status_code=422, detail=result.get("error") or "Route optimization failed.")
    except HTTPException:
        raise
    except (OSError, KeyError, TypeError, ValueError) as exc:
        LOGGER.exception("Fleet optimization failed.")
        raise HTTPException(status_code=503, detail="Fleet optimization could not be completed.") from exc

    previous_plans = db.query(Route).filter(Route.status == "planned").all()
    for old_route in previous_plans:
        old_route.status = "cancelled"
        for stop in db.query(RouteStop).filter(RouteStop.route_id == old_route.id).all():
            if stop.report_id:
                report = db.get(Report, stop.report_id)
                if report and report.status == "Assigned":
                    report.status = "Pending"
                    report.assigned_route_id = None
                    report.eta = None

    for location in locations:
        _location_prediction(location)
    db.flush()
    route_records: list[Route] = []
    route_note_inputs: dict[str, list[dict[str, Any]]] = {}
    for assignment in result["results"]:
        sequence = assignment["sequence"]
        if not sequence:
            continue
        vehicle = db.get(Vehicle, assignment["groupId"])
        if vehicle is None or vehicle.driver_id is None:
            continue
        route = Route(
            vehicle_id=vehicle.id,
            driver_id=vehicle.driver_id,
            status="planned",
            distance_km=assignment["routeDistanceKm"],
            duration_minutes=assignment["routeDurationMinutes"],
            current_waypoint_index=0,
            speed_multiplier=1,
            current_latitude=DEPOT["latitude"],
            current_longitude=DEPOT["longitude"],
        )
        db.add(route)
        db.flush()
        stop_notes: list[dict[str, Any]] = []
        for stop_data in assignment["schedule"]:
            target_type, target = node_targets[stop_data["nodeId"]]
            location_id = target.id if target_type == "location" else None
            report_id = target.id if target_type == "report" else None
            stop = RouteStop(
                route_id=route.id,
                sequence_number=len(stop_notes) + 1,
                location_id=location_id,
                report_id=report_id,
                name=stop_data["name"],
                latitude=target.latitude,
                longitude=target.longitude,
                waste_kg=stop_data["wasteKg"],
                eta=stop_data["arrivalTime"],
                status="Pending",
            )
            db.add(stop)
            note = {
                "sequenceNumber": len(stop_notes) + 1,
                "name": stop.name,
                "wasteType": target.waste_type if target_type == "report" else "General",
                "urgency": target.urgency if target_type == "report" else "medium",
            }
            stop_notes.append(note)
            if target_type == "report":
                target.status = "Assigned"
                target.assigned_route_id = route.id
                target.eta = stop.eta
        route_records.append(route)
        route_note_inputs[route.id] = stop_notes

    notes = await asyncio.gather(*(
        run_in_threadpool(llm_service.generate_driver_notes, route_note_inputs[route.id])
        for route in route_records
    ))
    for route, driver_notes in zip(route_records, notes):
        route.ai_route_notes = driver_notes["text"]
        route.ai_notes_source = driver_notes["source"]
    db.commit()
    return {
        "optimization": result,
        "routes": [_route_view(db, route) for route in route_records],
        "unassignedLocations": result["unassignedLocations"],
        "llmWarnings": [
            {"routeId": route.id, "warning": note["warning"]}
            for route, note in zip(route_records, notes)
            if note["warning"]
        ],
    }


@router.get("/llm/briefing")
def admin_briefing(
    db: Session = Depends(get_db),
    _: User = Depends(admin_only),
) -> dict[str, str]:
    pending = db.query(Report).filter(Report.status == "Pending").count()
    active = db.query(Route).filter(Route.status == "active").count()
    unavailable = db.query(Vehicle).filter(Vehicle.available.is_(False)).count()
    return llm_service.generate_admin_briefing({
        "pendingReports": pending,
        "activeRoutes": active,
        "unavailableVehicles": unavailable,
        "totalVehicles": db.query(Vehicle).count(),
    })


@router.get("/driver/route")
def driver_route(
    user: User = Depends(driver_only),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    route = (
        db.query(Route)
        .filter(Route.driver_id == user.id, Route.status.in_(("planned", "active", "paused")))
        .order_by((Route.status == "active").desc(), Route.created_at.desc())
        .first()
    )
    return {"route": _route_view(db, route) if route else None}


@router.post("/driver/route/start")
def start_driver_route(
    user: User = Depends(driver_only),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    route = _owned_driver_route(db, user)
    if route.status not in {"planned", "paused"}:
        raise HTTPException(status_code=409, detail="Only a planned or paused route can be started.")
    route.status = "active"
    route.started_at = route.started_at or utc_now()
    vehicle = db.get(Vehicle, route.vehicle_id)
    if vehicle:
        vehicle.available = False
    next_stop = (
        db.query(RouteStop)
        .filter(RouteStop.route_id == route.id, RouteStop.status != "Collected")
        .order_by(RouteStop.sequence_number)
        .first()
    )
    if next_stop:
        next_stop.status = "En Route"
        if next_stop.report_id:
            report = db.get(Report, next_stop.report_id)
            if report:
                report.status = "En Route"
    _refresh_route_etas(db, route)
    _event(db, route, "started")
    db.commit()
    return {"route": _route_view(db, route)}


@router.post("/driver/route/pause")
def pause_driver_route(
    user: User = Depends(driver_only),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    route = _owned_driver_route(db, user)
    if route.status != "active":
        raise HTTPException(status_code=409, detail="Only an active route can be paused.")
    route.status = "paused"
    _event(db, route, "paused")
    db.commit()
    return {"route": _route_view(db, route)}


@router.post("/driver/route/speed")
def set_driver_speed(
    payload: SimulationSpeed,
    user: User = Depends(driver_only),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    route = _owned_driver_route(db, user)
    if route.status not in {"active", "paused"}:
        raise HTTPException(status_code=409, detail="Start a route before changing its simulation speed.")
    route.speed_multiplier = payload.multiplier
    _event(db, route, "speed_changed", f"{payload.multiplier}x")
    db.commit()
    return {"route": _route_view(db, route)}


@router.post("/driver/route/location")
def update_driver_location(
    payload: DriverPosition,
    user: User = Depends(driver_only),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    latitude, longitude = payload.latitude, payload.longitude
    route = _owned_driver_route(db, user)
    if route.status != "active":
        raise HTTPException(status_code=409, detail="Only an active route accepts position updates.")
    route.current_latitude = float(latitude)
    route.current_longitude = float(longitude)
    vehicle = db.get(Vehicle, route.vehicle_id)
    if vehicle:
        vehicle.current_latitude = route.current_latitude
        vehicle.current_longitude = route.current_longitude
    _refresh_route_etas(db, route)
    db.commit()
    return {"currentPosition": {"latitude": route.current_latitude, "longitude": route.current_longitude}}


@router.post("/driver/route/stops/{stop_id}/complete")
def complete_driver_stop(
    stop_id: str,
    user: User = Depends(driver_only),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    route = _owned_driver_route(db, user)
    if route.status != "active":
        raise HTTPException(status_code=409, detail="Start the route before completing a stop.")
    stops = db.query(RouteStop).filter(RouteStop.route_id == route.id).order_by(RouteStop.sequence_number).all()
    next_stop = next((stop for stop in stops if stop.status != "Collected"), None)
    if next_stop is None or next_stop.id != stop_id or next_stop.status != "En Route":
        raise HTTPException(status_code=409, detail="Stops must be completed in their assigned order.")
    next_stop.status = "Collected"
    route.current_waypoint_index = next_stop.sequence_number
    route.current_latitude = next_stop.latitude
    route.current_longitude = next_stop.longitude
    vehicle = db.get(Vehicle, route.vehicle_id)
    if vehicle:
        vehicle.current_latitude = next_stop.latitude
        vehicle.current_longitude = next_stop.longitude
    if next_stop.location_id:
        location = db.get(Location, next_stop.location_id)
        if location:
            location.days_since_pickup = 0
            location.last_collected_kg = next_stop.waste_kg
            db.add(CollectionRecord(
                location_id=location.id,
                collected_kg=next_stop.waste_kg,
                day_of_week=utc_now().weekday(),
                rainfall_mm=0,
            ))
    if next_stop.report_id:
        report = db.get(Report, next_stop.report_id)
        if report:
            report.status = "Collected"
            report.eta = None
    following = next(
        (stop for stop in stops if stop.sequence_number > next_stop.sequence_number and stop.status != "Collected"),
        None,
    )
    if following:
        following.status = "En Route"
        if following.report_id:
            report = db.get(Report, following.report_id)
            if report:
                report.status = "En Route"
    else:
        route.status = "completed"
        route.completed_at = utc_now()
        route.current_latitude = DISPOSAL_SITE["latitude"]
        route.current_longitude = DISPOSAL_SITE["longitude"]
        if vehicle:
            vehicle.available = True
            vehicle.current_latitude = DISPOSAL_SITE["latitude"]
            vehicle.current_longitude = DISPOSAL_SITE["longitude"]
    if following:
        db.flush()
        _refresh_route_etas(db, route)
    _event(db, route, "stop_completed", next_stop.name)
    db.commit()
    return {"route": _route_view(db, route), "completedStopId": stop_id}


@router.get("/admin/simulation-events")
def simulation_events(
    db: Session = Depends(get_db),
    _: User = Depends(admin_only),
) -> dict[str, Any]:
    events = db.query(SimulationEvent).order_by(SimulationEvent.created_at.desc()).limit(100).all()
    return {"events": [{
        "id": event.id,
        "routeId": event.route_id,
        "eventType": event.event_type,
        "latitude": event.latitude,
        "longitude": event.longitude,
        "details": event.details,
        "createdAt": event.created_at.isoformat(),
    } for event in events]}


@router.get("/uploads/{filename}")
def get_report_photo(
    filename: str,
    user: User = Depends(authenticated),
    db: Session = Depends(get_db),
) -> FileResponse:
    if Path(filename).name != filename:
        raise HTTPException(status_code=404, detail="Image not found.")
    report = db.query(Report).filter(Report.photo_path == filename).first()
    if report is None:
        raise HTTPException(status_code=404, detail="Image not found.")
    if user.role == "citizen" and report.citizen_id != user.id:
        raise HTTPException(status_code=403, detail="This image belongs to another citizen.")
    if user.role == "driver" and not db.query(Route).filter(
        Route.id == report.assigned_route_id,
        Route.driver_id == user.id,
    ).first():
        raise HTTPException(status_code=403, detail="This image is not part of your assigned route.")
    photo_file = UPLOAD_DIR / filename
    if not photo_file.is_file():
        raise HTTPException(status_code=404, detail="Image file is unavailable.")
    return FileResponse(photo_file)

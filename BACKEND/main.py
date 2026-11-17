"""FastAPI entry point for the BuildX Challenge 05 waste-collection planner."""

from __future__ import annotations

import importlib
import inspect
import json
import logging
import os
from contextlib import asynccontextmanager
from functools import lru_cache
from pathlib import Path
from typing import Any, Literal

from fastapi import Body, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field, ValidationError
from starlette.concurrency import run_in_threadpool

LOGGER = logging.getLogger("buildx.api")
BACKEND_DIR = Path(__file__).resolve().parent
SEED_PATH = BACKEND_DIR / "data" / "sri_lanka_seed.json"


class ContractModel(BaseModel):
    class Config:
        extra = "forbid"


class Coordinate(ContractModel):
    latitude: float = Field(ge=-90, le=90)
    longitude: float = Field(ge=-180, le=180)


class Parameters(ContractModel):
    allowDisruptions: bool
    shiftStart: str = Field(pattern=r"^(?:[01]\d|2[0-3]):[0-5]\d$")
    serviceMinutesPerStop: float = Field(ge=0)
    averageSpeedKmh: float = Field(gt=0)
    roadDistanceFactor: float = Field(ge=1, le=3)


class Node(Coordinate):
    id: str = Field(min_length=1)
    name: str = Field(min_length=1)
    wasteKg: float = Field(ge=0)
    priority: int = Field(default=1, ge=1, le=5)
    attributes: list[str] = Field(default_factory=list)
    available: bool = True
    disrupted: bool = False


class Vehicle(ContractModel):
    id: str = Field(min_length=1)
    name: str = Field(min_length=1)
    type: str = Field(min_length=1)
    capacityKg: float = Field(gt=0)
    available: bool
    averageSpeedKmh: float | None = Field(default=None, gt=0)


class ProcessInput(ContractModel):
    scenarioId: str = Field(min_length=1)
    userPriority: Literal["cost_efficient", "balanced", "urgent"]
    parameters: Parameters
    depot: Coordinate
    vehicles: list[Vehicle] = Field(min_length=3)
    nodes: list[Node] = Field(min_length=20)


class SummaryMetrics(ContractModel):
    primaryScore: float
    totalDistanceOrCost: float
    unassignedCount: int
    assignedCount: int
    totalWasteKg: float
    collectedWasteKg: float
    averageVehicleUtilizationPercent: float
    executionTimeMs: float


class RouteStop(ContractModel):
    nodeId: str
    name: str
    arrivalTime: str
    wasteKg: float


class Assignment(ContractModel):
    groupId: str
    vehicleName: str
    vehicleType: str
    available: bool
    sequence: list[str]
    loadUsedKg: float
    loadCapacityKg: float
    utilizationPercent: float
    metricValue: float
    routeDistanceKm: float
    routeDurationMinutes: float
    schedule: list[RouteStop]


class BaselineComparison(ContractModel):
    baselineValue: float
    optimizedValue: float
    improvementPercent: float
    baselineUnassignedCount: int
    optimizedUnassignedCount: int


class UnassignedLocation(ContractModel):
    nodeId: str
    name: str
    wasteKg: float
    reason: str


class Explanation(ContractModel):
    targetId: str
    reason: str


class ProcessOutput(ContractModel):
    status: Literal["success", "error"]
    scenarioId: str | None
    algorithmUsed: str
    summaryMetrics: SummaryMetrics
    results: list[Assignment]
    baselineComparison: BaselineComparison
    unassignedLocations: list[UnassignedLocation]
    explainability: list[Explanation]
    error: str | None


class Scenario(ContractModel):
    scenarioId: str
    name: str
    description: str
    isSimulated: bool
    input: ProcessInput


class ScenarioCatalog(ContractModel):
    datasetId: str
    dataStatus: str
    disclaimer: str
    scenarios: list[Scenario]


def _load_engine() -> tuple[Any | None, Exception | None]:
    for module_name in (".engine", "engine"):
        try:
            if module_name.startswith("."):
                module = importlib.import_module(module_name, package=__package__)
            else:
                module = importlib.import_module(module_name)
            engine_run = getattr(module, "run_engine")
            if callable(engine_run):
                return engine_run, None
            raise TypeError("engine.run_engine is not callable")
        except (ImportError, AttributeError, TypeError) as exc:
            last_error = exc
    return None, last_error


engine_run, ENGINE_LOAD_ERROR = _load_engine()


@lru_cache(maxsize=1)
def _load_scenario_catalog() -> ScenarioCatalog:
    with SEED_PATH.open(encoding="utf-8") as seed_file:
        seed = json.load(seed_file)

    scenarios = []
    for definition in seed["scenarios"]:
        demand_field = definition["demandField"]
        nodes = [
            {
                "id": location["id"],
                "name": location["name"],
                "latitude": location["latitude"],
                "longitude": location["longitude"],
                "wasteKg": location[demand_field],
                "priority": location["priority"],
                "attributes": list(dict.fromkeys(
                    location["attributes"]
                    + (
                        ["overflowing"]
                        if location["disrupted"] and definition["parameters"]["allowDisruptions"]
                        else []
                    )
                )),
                "available": location["available"],
                "disrupted": location["disrupted"] and definition["parameters"]["allowDisruptions"],
            }
            for location in seed["locations"]
        ]
        scenario_input = {
            "scenarioId": definition["scenarioId"],
            "userPriority": definition["userPriority"],
            "parameters": definition["parameters"],
            "depot": seed["depot"],
            "vehicles": seed["vehicles"],
            "nodes": nodes,
        }
        scenarios.append({
            "scenarioId": definition["scenarioId"],
            "name": definition["name"],
            "description": definition["description"],
            "isSimulated": True,
            "input": scenario_input,
        })

    catalog = ScenarioCatalog.parse_obj({
        "datasetId": seed["datasetId"],
        "dataStatus": seed["dataStatus"],
        "disclaimer": seed["disclaimer"],
        "scenarios": scenarios,
    })
    if len(catalog.scenarios) != 2:
        raise ValueError("The Challenge 05 seed must define exactly two scenarios")
    if catalog.dataStatus.lower() != "simulated":
        raise ValueError("The Challenge 05 seed must identify its data as simulated")
    if catalog.scenarios[0].scenarioId == catalog.scenarios[1].scenarioId:
        raise ValueError("Scenario IDs must be distinct")
    return catalog


def _validation_details(exc: ValidationError) -> list[dict[str, Any]]:
    return [
        {
            "field": ".".join(str(part) for part in error["loc"]),
            "message": error["msg"],
        }
        for error in exc.errors()
    ]


def _frontend_origins() -> list[str]:
    configured = os.getenv(
        "FRONTEND_ORIGINS",
        "http://localhost:5173,http://127.0.0.1:5173,http://localhost:3000,http://127.0.0.1:3000",
    )
    return [origin.strip() for origin in configured.split(",") if origin.strip()]


@asynccontextmanager
async def lifespan(_: FastAPI):
    if __package__:
        from .seed import seed_database
        from .storage import validate_storage_configuration
    else:
        from seed import seed_database
        from storage import validate_storage_configuration
    validate_storage_configuration()
    await run_in_threadpool(seed_database)
    yield


app = FastAPI(
    title="BuildX Challenge 05 Waste Collection API",
    description="Waste fleet planning, citizen reports, route simulation, and ML/LLM-assisted workflows using simulated Sri Lankan data.",
    version="2.0.0",
    lifespan=lifespan,
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=_frontend_origins(),
    allow_credentials=True,
    allow_methods=["GET", "POST", "PATCH", "OPTIONS"],
    allow_headers=["Content-Type", "Authorization"],
)

try:
    from .workflows import router as workflow_router
except ImportError:
    from workflows import router as workflow_router
app.include_router(workflow_router)


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/api/v1/scenarios", response_model=ScenarioCatalog)
async def get_scenarios() -> ScenarioCatalog:
    try:
        return _load_scenario_catalog()
    except (OSError, json.JSONDecodeError, KeyError, ValidationError, ValueError) as exc:
        LOGGER.exception("Unable to load the Challenge 05 scenario seed")
        raise HTTPException(status_code=500, detail="Scenario data is unavailable or invalid.") from exc


@app.post("/api/v1/process", response_model=ProcessOutput)
async def process_scenario(payload: Any = Body(...)) -> ProcessOutput:
    if not isinstance(payload, dict):
        raise HTTPException(status_code=422, detail="Request body must be an object matching input-contract.json.")

    try:
        request = ProcessInput.parse_obj(payload)
    except ValidationError as exc:
        raise HTTPException(status_code=422, detail=_validation_details(exc)) from exc

    if engine_run is None:
        LOGGER.error("The waste collection engine could not be loaded: %s", ENGINE_LOAD_ERROR)
        raise HTTPException(status_code=503, detail="Waste collection engine is unavailable.")

    engine_payload = request.dict()
    result = await run_in_threadpool(engine_run, engine_payload)
    if inspect.isawaitable(result):
        result = await result
    if isinstance(result, BaseModel):
        result = result.dict()
    if not isinstance(result, dict):
        raise HTTPException(status_code=502, detail="Optimization engine returned an invalid response.")
    try:
        return ProcessOutput.parse_obj(result)
    except ValidationError as exc:
        LOGGER.exception("Waste collection engine response did not match output-contract.json")
        raise HTTPException(
            status_code=502,
            detail="Optimization engine response does not match output-contract.json.",
        ) from exc

"""FastAPI entry point for the BuildX Sri Lankan dispatch scenarios."""

from __future__ import annotations

import importlib
import inspect
import json
import logging
import os
from functools import lru_cache
from pathlib import Path
from typing import Any, Literal

from fastapi import Body, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field, ValidationError
from starlette.concurrency import run_in_threadpool

LOGGER = logging.getLogger("buildx.api")
BACKEND_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = BACKEND_DIR.parent
INPUT_CONTRACT_PATH = PROJECT_ROOT / "input-contract.json"
SEED_PATH = BACKEND_DIR / "data" / "sri_lanka_seed.json"


class ContractModel(BaseModel):
    class Config:
        extra = "forbid"


class Parameters(ContractModel):
    maxResources: int = Field(gt=0)
    capacityLimit: int = Field(gt=0)
    allowDisruptions: bool


class Node(ContractModel):
    id: str = Field(min_length=1)
    name: str = Field(min_length=1)
    latitude: float = Field(ge=-90, le=90)
    longitude: float = Field(ge=-180, le=180)
    demandOrLoad: int = Field(ge=0)
    attributes: list[str]


class ProcessInput(ContractModel):
    scenarioId: str = Field(min_length=1)
    userPriority: Literal["cost_efficient", "time_efficient", "balanced"]
    parameters: Parameters
    nodes: list[Node] = Field(min_length=1)


class SummaryMetrics(ContractModel):
    primaryScore: float
    totalDistanceOrCost: float
    unassignedCount: int
    executionTimeMs: float


class Assignment(ContractModel):
    groupId: str
    sequence: list[str]
    loadUsed: float
    loadCapacity: float
    metricValue: float


class BaselineComparison(ContractModel):
    baselineValue: float
    optimizedValue: float
    improvementPercent: float


class Explanation(ContractModel):
    targetId: str
    reason: str


class ProcessOutput(ContractModel):
    status: Literal["success", "error"]
    scenarioId: str
    algorithmUsed: str
    summaryMetrics: SummaryMetrics
    results: list[Assignment]
    baselineComparison: BaselineComparison
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
    """Find engine.run for both supported uvicorn import styles."""
    for module_name in (".engine", "engine"):
        try:
            if module_name.startswith("."):
                module = importlib.import_module(module_name, package=__package__)
            else:
                module = importlib.import_module(module_name)
            engine_run = getattr(module, "run")
            if not callable(engine_run):
                raise TypeError("engine.run is not callable")
            return engine_run, None
        except (ImportError, AttributeError, TypeError) as exc:
            last_error = exc
    return None, last_error


engine_run, ENGINE_LOAD_ERROR = _load_engine()


@lru_cache(maxsize=1)
def _load_input_contract() -> dict[str, Any]:
    with INPUT_CONTRACT_PATH.open(encoding="utf-8") as contract_file:
        contract = json.load(contract_file)
    if not isinstance(contract, dict):
        raise ValueError("input-contract.json must contain a JSON object")
    return contract


@lru_cache(maxsize=1)
def _load_scenario_catalog() -> ScenarioCatalog:
    with SEED_PATH.open(encoding="utf-8") as seed_file:
        raw_seed = json.load(seed_file)
    catalog = ScenarioCatalog.parse_obj(raw_seed)
    if len(catalog.scenarios) != 2:
        raise ValueError("The Sri Lankan seed must define exactly two scenarios")
    if catalog.dataStatus.lower() != "simulated":
        raise ValueError("The Sri Lankan seed must identify its data as simulated")
    if catalog.scenarios[0].input.scenarioId == catalog.scenarios[1].input.scenarioId:
        raise ValueError("Scenario IDs must be distinct")
    return catalog


def _validate_contract_shape(value: Any, template: Any, path: str = "$") -> None:
    """Ensure request keys and JSON value types follow the checked-in contract."""
    if isinstance(template, dict):
        if not isinstance(value, dict):
            raise ValueError(f"{path} must be an object")
        expected = set(template)
        received = set(value)
        missing = sorted(expected - received)
        unexpected = sorted(received - expected)
        if missing or unexpected:
            details = []
            if missing:
                details.append(f"missing keys: {', '.join(missing)}")
            if unexpected:
                details.append(f"unexpected keys: {', '.join(unexpected)}")
            raise ValueError(f"{path}: {'; '.join(details)}")
        for key, child_template in template.items():
            _validate_contract_shape(value[key], child_template, f"{path}.{key}")
        return

    if isinstance(template, list):
        if not isinstance(value, list):
            raise ValueError(f"{path} must be an array")
        if template:
            for index, item in enumerate(value):
                _validate_contract_shape(item, template[0], f"{path}[{index}]")
        return

    if isinstance(template, bool):
        valid = isinstance(value, bool)
    elif isinstance(template, int):
        valid = isinstance(value, int) and not isinstance(value, bool)
    elif isinstance(template, float):
        valid = isinstance(value, (int, float)) and not isinstance(value, bool)
    elif isinstance(template, str):
        valid = isinstance(value, str)
    else:
        valid = value is None if template is None else isinstance(value, type(template))

    if not valid:
        raise ValueError(f"{path} has the wrong JSON value type")


def _validation_details(exc: ValidationError) -> list[dict[str, Any]]:
    return [
        {
            "field": ".".join(str(part) for part in error["loc"]),
            "message": error["msg"],
        }
        for error in exc.errors()
    ]


def _frontend_origins() -> list[str]:
    configured = os.getenv("FRONTEND_ORIGINS", "http://localhost:3000,http://127.0.0.1:3000")
    return [origin.strip() for origin in configured.split(",") if origin.strip()]


app = FastAPI(
    title="BuildX Dispatch API",
    description="Scenario planning API with clearly simulated Sri Lankan seed data.",
    version="1.0.0",
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=_frontend_origins(),
    allow_credentials=True,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["Content-Type", "Authorization"],
)


@app.get("/api/v1/scenarios", response_model=ScenarioCatalog)
async def get_scenarios() -> ScenarioCatalog:
    try:
        return _load_scenario_catalog()
    except HTTPException:
        raise
    except (OSError, json.JSONDecodeError, ValidationError, ValueError) as exc:
        LOGGER.exception("Unable to load the Sri Lankan scenario seed")
        raise HTTPException(status_code=500, detail="Scenario data is unavailable or invalid.") from exc
    except Exception as exc:
        LOGGER.exception("Unexpected error while loading scenarios")
        raise HTTPException(status_code=500, detail="Unable to load scenarios.") from exc


@app.post("/api/v1/process", response_model=ProcessOutput)
async def process_scenario(payload: Any = Body(...)) -> ProcessOutput:
    try:
        if not isinstance(payload, dict):
            raise HTTPException(status_code=422, detail="Request body must be a JSON object matching input-contract.json.")

        try:
            _validate_contract_shape(payload, _load_input_contract())
        except (OSError, json.JSONDecodeError) as exc:
            LOGGER.exception("Unable to load input-contract.json")
            raise HTTPException(status_code=500, detail="Input contract is unavailable.") from exc
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc

        try:
            request = ProcessInput.parse_obj(payload)
        except ValidationError as exc:
            raise HTTPException(status_code=422, detail=_validation_details(exc)) from exc

        if not request.scenarioId.strip():
            raise HTTPException(status_code=422, detail="scenarioId must not be blank.")
        if any(not node.id.strip() or not node.name.strip() for node in request.nodes):
            raise HTTPException(status_code=422, detail="Each node must have a non-blank id and name.")
        node_ids = [node.id for node in request.nodes]
        if len(node_ids) != len(set(node_ids)):
            raise HTTPException(status_code=422, detail="Node IDs must be unique.")

        if engine_run is None:
            LOGGER.warning("Member 1 engine is unavailable: %s", ENGINE_LOAD_ERROR)
            raise HTTPException(status_code=503, detail="Optimization engine is not available yet.")

        engine_payload = request.dict(by_alias=True)
        result = await run_in_threadpool(engine_run, engine_payload)
        if inspect.isawaitable(result):
            result = await result
        if isinstance(result, BaseModel):
            result = result.dict(by_alias=True)
        if not isinstance(result, dict):
            raise HTTPException(status_code=502, detail="Optimization engine returned an invalid response.")

        try:
            return ProcessOutput.parse_obj(result)
        except ValidationError as exc:
            LOGGER.exception("Member 1 engine response did not match output-contract.json")
            raise HTTPException(status_code=502, detail="Optimization engine response does not match output-contract.json.") from exc
    except HTTPException:
        raise
    except Exception as exc:
        LOGGER.exception("Unexpected error while processing scenario")
        raise HTTPException(status_code=500, detail="Unable to process this scenario.") from exc
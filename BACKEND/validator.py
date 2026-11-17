import math
import re
from typing import Any


_PRIORITIES = {"cost_efficient", "balanced", "urgent"}
_START_TIME = re.compile(r"^(?:[01]\d|2[0-3]):[0-5]\d$")
_LOCATION_ATTRIBUTES = {
    "overflowing",
    "high_priority",
}


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def _number(value: Any, label: str, *, minimum: float = 0) -> float:
    _require(
        isinstance(value, (int, float)) and not isinstance(value, bool),
        f"{label} must be a number.",
    )
    result = float(value)
    _require(math.isfinite(result) and result >= minimum, f"{label} must be at least {minimum}.")
    return result


def _validate_coordinates(value: Any, label: str) -> None:
    _require(isinstance(value, dict), f"{label} must be an object.")
    latitude = _number(value.get("latitude"), f"{label}.latitude", minimum=-90)
    longitude = _number(value.get("longitude"), f"{label}.longitude", minimum=-180)
    _require(latitude <= 90, f"{label}.latitude must be at most 90.")
    _require(longitude <= 180, f"{label}.longitude must be at most 180.")


def validate_input(data: Any) -> None:
    _require(isinstance(data, dict), "Input must be an object.")
    required = {"scenarioId", "userPriority", "parameters", "depot", "vehicles", "nodes"}
    _require(required.issubset(data), f"Input is missing required fields: {', '.join(sorted(required - data.keys()))}.")
    _require(isinstance(data["scenarioId"], str) and data["scenarioId"].strip(), "scenarioId must be a non-empty string.")
    _require(data["userPriority"] in _PRIORITIES, f"userPriority must be one of: {', '.join(sorted(_PRIORITIES))}.")

    parameters = data["parameters"]
    _require(isinstance(parameters, dict), "parameters must be an object.")
    _require(isinstance(parameters.get("allowDisruptions"), bool), "parameters.allowDisruptions must be a boolean.")
    _require(
        isinstance(parameters.get("shiftStart"), str) and _START_TIME.fullmatch(parameters["shiftStart"]),
        "parameters.shiftStart must use 24-hour HH:MM format.",
    )
    _number(parameters.get("serviceMinutesPerStop"), "parameters.serviceMinutesPerStop")
    _number(parameters.get("averageSpeedKmh"), "parameters.averageSpeedKmh", minimum=0.1)
    road_factor = _number(parameters.get("roadDistanceFactor"), "parameters.roadDistanceFactor", minimum=1)
    _require(road_factor <= 3, "parameters.roadDistanceFactor must not exceed 3.")

    _validate_coordinates(data["depot"], "depot")
    vehicles = data["vehicles"]
    _require(isinstance(vehicles, list) and len(vehicles) >= 3, "At least three vehicles are required.")
    vehicle_ids: set[str] = set()
    capacities: set[float] = set()
    for index, vehicle in enumerate(vehicles):
        label = f"vehicles[{index}]"
        _require(isinstance(vehicle, dict), f"{label} must be an object.")
        for field in ("id", "name", "type"):
            _require(isinstance(vehicle.get(field), str) and vehicle[field].strip(), f"{label}.{field} must be a non-empty string.")
        _require(vehicle["id"] not in vehicle_ids, f"Vehicle id {vehicle['id']} is duplicated.")
        vehicle_ids.add(vehicle["id"])
        capacity = _number(vehicle.get("capacityKg"), f"{label}.capacityKg", minimum=0.1)
        capacities.add(capacity)
        _require(isinstance(vehicle.get("available"), bool), f"{label}.available must be a boolean.")
        if vehicle.get("averageSpeedKmh") is not None:
            _number(vehicle["averageSpeedKmh"], f"{label}.averageSpeedKmh", minimum=0.1)
    _require(len(capacities) >= 3, "At least three distinct vehicle capacities are required.")

    nodes = data["nodes"]
    _require(isinstance(nodes, list) and len(nodes) >= 1, "At least one collection location is required.")
    node_ids: set[str] = set()
    for index, node in enumerate(nodes):
        label = f"nodes[{index}]"
        _require(isinstance(node, dict), f"{label} must be an object.")
        for field in ("id", "name"):
            _require(isinstance(node.get(field), str) and node[field].strip(), f"{label}.{field} must be a non-empty string.")
        _require(node["id"] not in node_ids, f"Collection location id {node['id']} is duplicated.")
        node_ids.add(node["id"])
        _validate_coordinates(node, label)
        _number(node.get("wasteKg"), f"{label}.wasteKg")
        priority = node.get("priority", 1)
        _require(
            isinstance(priority, int) and not isinstance(priority, bool) and 1 <= priority <= 5,
            f"{label}.priority must be an integer from 1 to 5.",
        )
        attributes = node.get("attributes", [])
        _require(isinstance(attributes, list), f"{label}.attributes must be an array.")
        _require(
            all(isinstance(item, str) and item in _LOCATION_ATTRIBUTES for item in attributes),
            f"{label}.attributes contains an unsupported value.",
        )
        for field in ("available", "disrupted"):
            if field in node:
                _require(isinstance(node[field], bool), f"{label}.{field} must be a boolean.")

"""Input validation for the BuildX routing engine."""

from __future__ import annotations

import math
from typing import Any


PRIORITIES = {"cost_efficient", "balanced", "urgent"}


def _is_number(value: Any) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value)


def validate_input(data: Any) -> dict[str, Any]:
    """Validate an input-contract payload, raising ValueError with a useful message."""
    if not isinstance(data, dict):
        raise ValueError("Input must be a JSON object.")

    scenario_id = data.get("scenarioId")
    if not isinstance(scenario_id, str) or not scenario_id.strip():
        raise ValueError("'scenarioId' must be a non-empty string.")

    priority = data.get("userPriority")
    if not isinstance(priority, str) or priority not in PRIORITIES:
        raise ValueError(f"'userPriority' must be one of {', '.join(sorted(PRIORITIES))}.")

    parameters = data.get("parameters")
    if not isinstance(parameters, dict):
        raise ValueError("'parameters' must be an object.")

    max_resources = parameters.get("maxResources")
    if not isinstance(max_resources, int) or isinstance(max_resources, bool) or max_resources < 1:
        raise ValueError("'parameters.maxResources' must be a positive integer.")

    capacity_limit = parameters.get("capacityLimit")
    if not _is_number(capacity_limit) or capacity_limit <= 0:
        raise ValueError("'parameters.capacityLimit' must be a finite positive number.")

    if not isinstance(parameters.get("allowDisruptions"), bool):
        raise ValueError("'parameters.allowDisruptions' must be a boolean.")

    nodes = data.get("nodes")
    if not isinstance(nodes, list):
        raise ValueError("'nodes' must be an array.")

    node_ids: set[str] = set()
    for index, node in enumerate(nodes):
        prefix = f"'nodes[{index}]'"
        if not isinstance(node, dict):
            raise ValueError(f"{prefix} must be an object.")

        node_id = node.get("id")
        if not isinstance(node_id, str) or not node_id.strip():
            raise ValueError(f"{prefix}.id must be a non-empty string.")
        if node_id in node_ids:
            raise ValueError(f"Node id '{node_id}' is duplicated.")
        node_ids.add(node_id)

        if not isinstance(node.get("name"), str) or not node["name"].strip():
            raise ValueError(f"{prefix}.name must be a non-empty string.")

        latitude = node.get("latitude")
        longitude = node.get("longitude")
        if not _is_number(latitude) or not -90 <= latitude <= 90:
            raise ValueError(f"{prefix}.latitude must be between -90 and 90.")
        if not _is_number(longitude) or not -180 <= longitude <= 180:
            raise ValueError(f"{prefix}.longitude must be between -180 and 180.")

        demand = node.get("demandOrLoad")
        if not _is_number(demand) or demand < 0:
            raise ValueError(f"{prefix}.demandOrLoad must be a finite non-negative number.")

        attributes = node.get("attributes", [])
        if not isinstance(attributes, list) or any(not isinstance(item, str) for item in attributes):
            raise ValueError(f"{prefix}.attributes must be an array of strings.")

        for flag in ("available", "disrupted"):
            if flag in node and not isinstance(node[flag], bool):
                raise ValueError(f"{prefix}.{flag} must be a boolean.")

        if "risk" in node and (not _is_number(node["risk"]) or not 0 <= node["risk"] <= 1):
            raise ValueError(f"{prefix}.risk must be a finite number between 0 and 1.")

    return data

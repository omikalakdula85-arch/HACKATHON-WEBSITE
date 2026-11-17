"""Deterministic capacity-constrained routing and baseline comparison."""

from __future__ import annotations

import math
import time
from typing import Any

try:
    from .validator import validate_input
except ImportError:
    from validator import validate_input


EARTH_RADIUS_KM = 6371.0088
RISK_WEIGHT_BY_PRIORITY = {
    "cost_efficient": 0.5,
    "balanced": 1.0,
    "urgent": 2.0,
}
UNAVAILABLE_ATTRIBUTES = {"blocked", "closed", "unavailable"}
DISRUPTION_ATTRIBUTES = {"disrupted"}


def haversine_km(first: dict[str, Any], second: dict[str, Any]) -> float:
    """Return great-circle distance between two contract nodes, in kilometres."""
    lat1, lon1 = math.radians(first["latitude"]), math.radians(first["longitude"])
    lat2, lon2 = math.radians(second["latitude"]), math.radians(second["longitude"])
    delta_lat = lat2 - lat1
    delta_lon = lon2 - lon1
    hav = (
        math.sin(delta_lat / 2) ** 2
        + math.cos(lat1) * math.cos(lat2) * math.sin(delta_lon / 2) ** 2
    )
    return 2 * EARTH_RADIUS_KM * math.asin(math.sqrt(min(1.0, hav)))


def _risk(node: dict[str, Any], disrupted: bool) -> float:
    if "risk" in node:
        return float(node["risk"])
    attributes = set(node.get("attributes", []))
    if "high_risk" in attributes:
        return 0.75
    if "medium_risk" in attributes:
        return 0.4
    if disrupted:
        return 0.5
    return 0.0


def _route_cost(
    route: list[dict[str, Any]], risks: dict[str, float], risk_weight: float
) -> float:
    cost = 0.0
    for first, second in zip(route, route[1:]):
        average_risk = (risks[first["id"]] + risks[second["id"]]) / 2
        cost += haversine_km(first, second) * (1 + risk_weight * average_risk)
    return cost


def _baseline(
    nodes: list[dict[str, Any]], capacity: float, max_resources: int
) -> tuple[list[list[dict[str, Any]]], list[dict[str, Any]]]:
    """Pack in input order and preserve that order within each resource route."""
    routes: list[list[dict[str, Any]]] = []
    loads: list[float] = []
    unassigned: list[dict[str, Any]] = []
    for node in nodes:
        demand = node["demandOrLoad"]
        if demand > capacity:
            unassigned.append(node)
            continue
        for index, load in enumerate(loads):
            if load + demand <= capacity + 1e-9:
                routes[index].append(node)
                loads[index] += demand
                break
        else:
            if len(routes) < max_resources:
                routes.append([node])
                loads.append(demand)
            else:
                unassigned.append(node)
    return routes, unassigned


def _best_insertion(
    node: dict[str, Any],
    routes: list[list[dict[str, Any]]],
    loads: list[float],
    capacity: float,
    max_resources: int,
    risks: dict[str, float],
    risk_weight: float,
) -> tuple[int | None, int, float] | None:
    best: tuple[float, int, int, int] | None = None
    demand = node["demandOrLoad"]
    for route_index, route in enumerate(routes):
        if loads[route_index] + demand > capacity + 1e-9:
            continue
        before = _route_cost(route, risks, risk_weight)
        for position in range(len(route) + 1):
            candidate = route[:position] + [node] + route[position:]
            delta = _route_cost(candidate, risks, risk_weight) - before
            key = (delta, 0, route_index, position)
            if best is None or key < best:
                best = key

    if best is None and len(routes) < max_resources:
        new_route_key = (_route_cost([node], risks, risk_weight), 1, len(routes), 0)
        best = new_route_key

    if best is None:
        return None
    return (None if best[1] else best[2], best[3], best[0])


def _construct_routes(
    nodes: list[dict[str, Any]],
    capacity: float,
    max_resources: int,
    risks: dict[str, float],
    risk_weight: float,
) -> tuple[list[list[dict[str, Any]]], list[dict[str, Any]]]:
    routes: list[list[dict[str, Any]]] = []
    loads: list[float] = []
    unassigned: list[dict[str, Any]] = []
    priority_nodes = sorted(
        nodes,
        key=lambda node: (
            -node["demandOrLoad"],
            -risks[node["id"]],
            node["id"],
        ),
    )

    for node in priority_nodes:
        demand = node["demandOrLoad"]
        if demand > capacity:
            unassigned.append(node)
            continue
        insertion = _best_insertion(
            node, routes, loads, capacity, max_resources, risks, risk_weight
        )
        if insertion is None:
            unassigned.append(node)
            continue
        route_index, position, _ = insertion
        if route_index is None:
            routes.append([node])
            loads.append(demand)
        else:
            routes[route_index].insert(position, node)
            loads[route_index] += demand
    return routes, unassigned


def _improve_routes(
    routes: list[list[dict[str, Any]]],
    capacity: float,
    risks: dict[str, float],
    risk_weight: float,
) -> None:
    """Apply improving 2-opt reversals and capacity-safe inter-route relocations."""
    for route in routes:
        improved = True
        while improved:
            improved = False
            current_cost = _route_cost(route, risks, risk_weight)
            best_route = route
            best_cost = current_cost
            for start in range(len(route) - 1):
                for end in range(start + 1, len(route)):
                    candidate = route[:start] + list(reversed(route[start : end + 1])) + route[end + 1 :]
                    candidate_cost = _route_cost(candidate, risks, risk_weight)
                    if candidate_cost < best_cost - 1e-9:
                        best_route, best_cost = candidate, candidate_cost
            if best_cost < current_cost - 1e-9:
                route[:] = best_route
                improved = True

    route_loads = [
        sum(node["demandOrLoad"] for node in route)
        for route in routes
    ]
    max_rounds = max(1, sum(len(route) for route in routes) * 2)
    for _ in range(max_rounds):
        best_move: tuple[float, int, int, int, int, int] | None = None
        for source_index, source in enumerate(routes):
            for source_position, node in enumerate(source):
                demand = node["demandOrLoad"]
                for destination_index, destination in enumerate(routes):
                    if source_index == destination_index:
                        continue
                    if route_loads[destination_index] + demand > capacity + 1e-9:
                        continue
                    before = _route_cost(source, risks, risk_weight) + _route_cost(
                        destination, risks, risk_weight
                    )
                    shortened = source[:source_position] + source[source_position + 1 :]
                    for destination_position in range(len(destination) + 1):
                        extended = (
                            destination[:destination_position]
                            + [node]
                            + destination[destination_position:]
                        )
                        after = _route_cost(shortened, risks, risk_weight) + _route_cost(
                            extended, risks, risk_weight
                        )
                        delta = after - before
                        candidate = (
                            delta,
                            0,
                            source_index,
                            source_position,
                            destination_index,
                            destination_position,
                        )
                        if delta < -1e-9 and (
                            best_move is None or candidate < best_move
                        ):
                            best_move = candidate
                    for destination_position, other in enumerate(destination):
                        source_load = route_loads[source_index] - demand + other["demandOrLoad"]
                        destination_load = (
                            route_loads[destination_index]
                            - other["demandOrLoad"]
                            + demand
                        )
                        if (
                            source_load > capacity + 1e-9
                            or destination_load > capacity + 1e-9
                        ):
                            continue
                        source_after = source[:]
                        destination_after = destination[:]
                        source_after[source_position] = other
                        destination_after[destination_position] = node
                        after = _route_cost(
                            source_after, risks, risk_weight
                        ) + _route_cost(destination_after, risks, risk_weight)
                        delta = after - before
                        candidate = (
                            delta,
                            1,
                            source_index,
                            source_position,
                            destination_index,
                            destination_position,
                        )
                        if delta < -1e-9 and (
                            best_move is None or candidate < best_move
                        ):
                            best_move = candidate
        if best_move is None:
            break
        (
            _,
            move_type,
            source_index,
            source_position,
            destination_index,
            destination_position,
        ) = best_move
        if move_type == 0:
            node = routes[source_index].pop(source_position)
            routes[destination_index].insert(destination_position, node)
            route_loads[source_index] -= node["demandOrLoad"]
            route_loads[destination_index] += node["demandOrLoad"]
        else:
            first = routes[source_index][source_position]
            second = routes[destination_index][destination_position]
            routes[source_index][source_position] = second
            routes[destination_index][destination_position] = first
            route_loads[source_index] += second["demandOrLoad"] - first["demandOrLoad"]
            route_loads[destination_index] += first["demandOrLoad"] - second["demandOrLoad"]

    for index in range(len(routes) - 1, -1, -1):
        if not routes[index]:
            routes.pop(index)


def _resource_id(index: int) -> str:
    value = index + 1
    label = ""
    while value:
        value, remainder = divmod(value - 1, 26)
        label = chr(ord("A") + remainder) + label
    return f"Resource_{label}"


def _error_output(scenario_id: str, message: str) -> dict[str, Any]:
    return {
        "status": "error",
        "scenarioId": scenario_id,
        "algorithmUsed": "Capacity-Constrained Multi-Criteria Routing",
        "summaryMetrics": {
            "primaryScore": 0.0,
            "totalDistanceOrCost": 0.0,
            "unassignedCount": 0,
            "executionTimeMs": 0,
        },
        "results": [],
        "baselineComparison": {
            "baselineValue": 0.0,
            "optimizedValue": 0.0,
            "improvementPercent": 0.0,
        },
        "explainability": [],
        "error": message,
    }


def run_engine(data: Any) -> dict[str, Any]:
    """Validate a contract payload and return a contract-shaped optimization result."""
    scenario_id = data.get("scenarioId", "") if isinstance(data, dict) else ""
    try:
        validate_input(data)
    except (TypeError, ValueError) as error:
        return _error_output(scenario_id if isinstance(scenario_id, str) else "", str(error))

    started = time.perf_counter()
    parameters = data["parameters"]
    capacity = float(parameters["capacityLimit"])
    max_resources = parameters["maxResources"]
    allow_disruptions = parameters["allowDisruptions"]
    priority = data["userPriority"]
    risk_weight = RISK_WEIGHT_BY_PRIORITY[priority]

    schedulable: list[dict[str, Any]] = []
    unassigned_reasons: dict[str, str] = {}
    risks: dict[str, float] = {}
    for node in data["nodes"]:
        attributes = set(node.get("attributes", []))
        disrupted = node.get("disrupted", False) or bool(
            attributes & DISRUPTION_ATTRIBUTES
        )
        risks[node["id"]] = _risk(node, disrupted)
        if node.get("available", True) is False or attributes & UNAVAILABLE_ATTRIBUTES:
            unassigned_reasons[node["id"]] = "It is marked unavailable, so it was not assigned."
        elif disrupted and not allow_disruptions:
            unassigned_reasons[node["id"]] = (
                "It is disrupted and disruptions are disabled for this scenario."
            )
        else:
            schedulable.append(node)

    baseline_routes, baseline_unassigned = _baseline(
        schedulable, capacity, max_resources
    )
    optimized_routes, optimized_unassigned = _construct_routes(
        schedulable, capacity, max_resources, risks, risk_weight
    )
    _improve_routes(optimized_routes, capacity, risks, risk_weight)

    for node in optimized_unassigned:
        if node["demandOrLoad"] > capacity:
            unassigned_reasons.setdefault(
                node["id"], "Its load exceeds the capacity limit of every resource."
            )
        else:
            unassigned_reasons.setdefault(
                node["id"], "No remaining resource has enough capacity."
            )

    optimized_cost = sum(
        _route_cost(route, risks, risk_weight) for route in optimized_routes
    )
    baseline_cost = sum(
        _route_cost(route, risks, risk_weight) for route in baseline_routes
    )
    improvement = (
        (baseline_cost - optimized_cost) / baseline_cost * 100
        if baseline_cost > 0
        else 0.0
    )
    total_demand = sum(node["demandOrLoad"] for node in data["nodes"])
    assigned_demand = sum(
        node["demandOrLoad"] for route in optimized_routes for node in route
    )
    primary_score = (
        100.0 if total_demand == 0 else assigned_demand / total_demand * 100
    )

    results: list[dict[str, Any]] = []
    explanations: list[dict[str, str]] = []
    for index, route in enumerate(optimized_routes):
        resource_id = _resource_id(index)
        load_used = sum(node["demandOrLoad"] for node in route)
        results.append(
            {
                "groupId": resource_id,
                "sequence": [node["id"] for node in route],
                "loadUsed": load_used,
                "loadCapacity": parameters["capacityLimit"],
                "metricValue": _route_cost(route, risks, risk_weight),
            }
        )
        for position, node in enumerate(route):
            prior = route[position - 1]["id"] if position else "the route start"
            disruption_note = (
                " It was accepted despite disruption because disruptions are enabled."
                if (
                    (node.get("disrupted", False)
                     or set(node.get("attributes", [])) & DISRUPTION_ATTRIBUTES)
                    and allow_disruptions
                )
                else ""
            )
            explanations.append(
                {
                    "targetId": node["id"],
                    "reason": (
                        f"Assigned to {resource_id} after {prior}; the route stays within "
                        f"capacity ({load_used:g}/{capacity:g}) and was selected to reduce "
                        f"distance and risk-weighted travel.{disruption_note}"
                    ),
                }
            )

    for node in data["nodes"]:
        if node["id"] in unassigned_reasons:
            explanations.append(
                {"targetId": node["id"], "reason": unassigned_reasons[node["id"]]}
            )
    explanations.append(
        {
            "targetId": "general",
            "reason": (
                f"The optimized routes cost {optimized_cost:.2f} versus "
                f"{baseline_cost:.2f} for the input-order greedy baseline "
                f"({improvement:.2f}% improvement)."
            ),
        }
    )

    return {
        "status": "success",
        "scenarioId": data["scenarioId"],
        "algorithmUsed": "Capacity-Constrained Multi-Criteria Routing",
        "summaryMetrics": {
            "primaryScore": primary_score,
            "totalDistanceOrCost": optimized_cost,
            "unassignedCount": len(data["nodes"])
            - sum(len(route) for route in optimized_routes),
            "executionTimeMs": round((time.perf_counter() - started) * 1000, 3),
        },
        "results": results,
        "baselineComparison": {
            "baselineValue": baseline_cost,
            "optimizedValue": optimized_cost,
            "improvementPercent": improvement,
        },
        "explainability": explanations,
        "error": None,
    }

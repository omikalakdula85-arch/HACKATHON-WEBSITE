import math
import time
from typing import Any

try:
    from .validator import validate_input
except ImportError:
    from validator import validate_input


EARTH_RADIUS_KM = 6371.0088


def haversine_km(point_a: dict[str, Any], point_b: dict[str, Any]) -> float:
    """Return great-circle distance between two latitude/longitude points."""
    lat_a = math.radians(float(point_a["latitude"]))
    lat_b = math.radians(float(point_b["latitude"]))
    delta_lat = lat_b - lat_a
    delta_lon = math.radians(float(point_b["longitude"]) - float(point_a["longitude"]))
    hav = math.sin(delta_lat / 2) ** 2 + math.cos(lat_a) * math.cos(lat_b) * math.sin(delta_lon / 2) ** 2
    return EARTH_RADIUS_KM * 2 * math.asin(math.sqrt(min(1.0, hav)))


def _distance(point_a: dict[str, Any], point_b: dict[str, Any], road_factor: float) -> float:
    return haversine_km(point_a, point_b) * road_factor


def _route_distance(
    route: list[str],
    nodes_by_id: dict[str, dict[str, Any]],
    depot: dict[str, Any],
    road_factor: float,
) -> float:
    if not route:
        return 0.0
    distance = _distance(depot, nodes_by_id[route[0]], road_factor)
    for first, second in zip(route, route[1:]):
        distance += _distance(nodes_by_id[first], nodes_by_id[second], road_factor)
    return distance + _distance(nodes_by_id[route[-1]], depot, road_factor)


def _route_load(route: list[str], nodes_by_id: dict[str, dict[str, Any]]) -> float:
    return sum(float(nodes_by_id[node_id]["wasteKg"]) for node_id in route)


def _route_priority(route: list[str], nodes_by_id: dict[str, dict[str, Any]]) -> float:
    score = 0.0
    for node_id in route:
        node = nodes_by_id[node_id]
        attributes = set(node.get("attributes", []))
        multiplier = int(node.get("priority", 1))
        if attributes.intersection({"overflowing", "high_priority"}):
            multiplier += 1
        score += float(node["wasteKg"]) * multiplier
    return score


def _two_opt(
    route: list[str],
    nodes_by_id: dict[str, dict[str, Any]],
    depot: dict[str, Any],
    road_factor: float,
) -> list[str]:
    best = route[:]
    best_distance = _route_distance(best, nodes_by_id, depot, road_factor)
    improved = True
    while improved:
        improved = False
        for start in range(len(best) - 1):
            for end in range(start + 2, len(best) + 1):
                candidate = best[:start] + list(reversed(best[start:end])) + best[end:]
                candidate_distance = _route_distance(candidate, nodes_by_id, depot, road_factor)
                if candidate_distance + 1e-9 < best_distance:
                    best = candidate
                    best_distance = candidate_distance
                    improved = True
    return best


def _join_routes(
    first: list[str],
    second: list[str],
    first_id: str,
    second_id: str,
) -> list[str] | None:
    first_options = (first, list(reversed(first)))
    second_options = (second, list(reversed(second)))
    for route_a in first_options:
        for route_b in second_options:
            if route_a[-1] == first_id and route_b[0] == second_id:
                return route_a + route_b
            if route_b[-1] == first_id and route_a[0] == second_id:
                return route_b + route_a
    return None


def _clarke_wright_routes(
    nodes: list[dict[str, Any]],
    vehicles: list[dict[str, Any]],
    depot: dict[str, Any],
    road_factor: float,
) -> list[list[str]]:
    if not nodes or not vehicles:
        return []
    nodes_by_id = {node["id"]: node for node in nodes}
    routes: list[list[str] | None] = [[node["id"]] for node in nodes]
    route_for_node = {node["id"]: index for index, node in enumerate(nodes)}
    maximum_capacity = max(float(vehicle["capacityKg"]) for vehicle in vehicles)
    capacities = sorted(float(vehicle["capacityKg"]) for vehicle in vehicles)
    target_route_count = min(len(vehicles), len(nodes))
    active_route_count = len(routes)
    savings: list[tuple[float, str, str]] = []
    for index, first in enumerate(nodes):
        for second in nodes[index + 1:]:
            saving = (
                _distance(depot, first, road_factor)
                + _distance(depot, second, road_factor)
                - _distance(first, second, road_factor)
            )
            if saving > 0:
                savings.append((saving, first["id"], second["id"]))
    savings.sort(key=lambda item: (-item[0], item[1], item[2]))

    for _, first_id, second_id in savings:
        if active_route_count <= target_route_count:
            break
        first_index = route_for_node[first_id]
        second_index = route_for_node[second_id]
        if first_index == second_index:
            continue
        first_route = routes[first_index]
        second_route = routes[second_index]
        if first_route is None or second_route is None:
            continue
        candidate = _join_routes(first_route, second_route, first_id, second_id)
        if candidate is None:
            continue
        candidate_load = _route_load(candidate, nodes_by_id)
        if candidate_load > maximum_capacity + 1e-9:
            continue
        remaining_loads = [
            _route_load(route, nodes_by_id)
            for index, route in enumerate(routes)
            if route is not None and index not in {first_index, second_index}
        ]
        remaining_loads.append(candidate_load)
        if any(
            sum(load > capacity + 1e-9 for load in remaining_loads)
            > sum(vehicle_capacity > capacity for vehicle_capacity in capacities)
            for capacity in capacities[:-1]
        ):
            continue
        routes[first_index] = candidate
        routes[second_index] = None
        active_route_count -= 1
        for node_id in candidate:
            route_for_node[node_id] = first_index

    return [
        _two_opt(route, nodes_by_id, depot, road_factor)
        for route in routes
        if route is not None
    ]


def _minutes_after(start_minutes: int, elapsed_minutes: float) -> str:
    total_minutes = start_minutes + round(elapsed_minutes)
    day_offset, minute_of_day = divmod(total_minutes, 24 * 60)
    result = f"{minute_of_day // 60:02d}:{minute_of_day % 60:02d}"
    return f"{result} (+{day_offset}d)" if day_offset else result


def _schedule_route(
    route: list[str],
    nodes_by_id: dict[str, dict[str, Any]],
    depot: dict[str, Any],
    parameters: dict[str, Any],
    vehicle: dict[str, Any],
) -> tuple[list[dict[str, Any]], float, float]:
    if not route:
        return [], 0.0, 0.0
    speed = float(vehicle.get("averageSpeedKmh") or parameters["averageSpeedKmh"])
    service_minutes = float(parameters["serviceMinutesPerStop"])
    road_factor = float(parameters["roadDistanceFactor"])
    hour, minute = map(int, parameters["shiftStart"].split(":"))
    start_minutes = hour * 60 + minute
    elapsed_minutes = 0.0
    previous = depot
    schedule: list[dict[str, Any]] = []
    for node_id in route:
        node = nodes_by_id[node_id]
        leg = _distance(previous, node, road_factor)
        elapsed_minutes += leg / speed * 60
        schedule.append({
            "nodeId": node_id,
            "name": node["name"],
            "arrivalTime": _minutes_after(start_minutes, elapsed_minutes),
            "wasteKg": float(node["wasteKg"]),
        })
        elapsed_minutes += service_minutes
        previous = node
    elapsed_minutes += _distance(previous, depot, road_factor) / speed * 60
    distance = _route_distance(route, nodes_by_id, depot, road_factor)
    return schedule, distance, elapsed_minutes


def _choose_route_assignments(
    routes: list[list[str]],
    nodes_by_id: dict[str, dict[str, Any]],
    vehicles: list[dict[str, Any]],
    depot: dict[str, Any],
    road_factor: float,
    user_priority: str,
) -> dict[str, list[str]]:
    ordered_vehicles = sorted(
        (vehicle for vehicle in vehicles if vehicle["available"]),
        key=lambda vehicle: (-float(vehicle["capacityKg"]), vehicle["id"]),
    )
    assignments = {vehicle["id"]: [] for vehicle in ordered_vehicles}
    if len(ordered_vehicles) > 4:
        remaining = set(range(len(routes)))
        for vehicle in ordered_vehicles:
            feasible = [
                index for index in remaining
                if _route_load(routes[index], nodes_by_id) <= float(vehicle["capacityKg"]) + 1e-9
            ]
            if feasible:
                chosen = max(
                    feasible,
                    key=lambda index: (
                        _route_priority(routes[index], nodes_by_id)
                        if user_priority == "urgent"
                        else _route_load(routes[index], nodes_by_id),
                        -_route_distance(routes[index], nodes_by_id, depot, road_factor)
                        if user_priority == "cost_efficient"
                        else _route_load(routes[index], nodes_by_id),
                    ),
                )
                assignments[vehicle["id"]] = routes[chosen]
                remaining.remove(chosen)
        return assignments

    best_key: tuple[float, float, float] = (-math.inf, -math.inf, -math.inf)
    best_assignments = assignments.copy()
    working = assignments.copy()

    def search(vehicle_index: int, used_routes: set[int], collected: float, priority: float, distance: float) -> None:
        nonlocal best_key, best_assignments
        if vehicle_index == len(ordered_vehicles):
            if user_priority == "urgent":
                key = (priority, collected, -distance)
            elif user_priority == "cost_efficient":
                key = (collected, -distance, priority)
            else:
                key = (collected, priority, -distance)
            if key > best_key:
                best_key = key
                best_assignments = working.copy()
            return

        vehicle = ordered_vehicles[vehicle_index]
        capacity = float(vehicle["capacityKg"])
        for route_index, route in enumerate(routes):
            if route_index in used_routes:
                continue
            load = _route_load(route, nodes_by_id)
            if load > capacity + 1e-9:
                continue
            working[vehicle["id"]] = route
            used_routes.add(route_index)
            search(
                vehicle_index + 1,
                used_routes,
                collected + load,
                priority + _route_priority(route, nodes_by_id),
                distance + _route_distance(route, nodes_by_id, depot, road_factor),
            )
            used_routes.remove(route_index)
        working[vehicle["id"]] = []
        search(vehicle_index + 1, used_routes, collected, priority, distance)

    search(0, set(), 0.0, 0.0, 0.0)
    return best_assignments


def _input_order_baseline(
    assignments: dict[str, list[str]],
    nodes: list[dict[str, Any]],
) -> dict[str, list[str]]:
    input_order = {node["id"]: index for index, node in enumerate(nodes)}
    return {
        vehicle_id: sorted(route, key=input_order.__getitem__)
        for vehicle_id, route in assignments.items()
    }


def _error_output(scenario_id: str | None, message: str) -> dict[str, Any]:
    return {
        "status": "error",
        "scenarioId": scenario_id,
        "algorithmUsed": "Heterogeneous CVRP: Clarke-Wright Savings + 2-opt",
        "summaryMetrics": {
            "primaryScore": 0.0,
            "totalDistanceOrCost": 0.0,
            "unassignedCount": 0,
            "assignedCount": 0,
            "totalWasteKg": 0.0,
            "collectedWasteKg": 0.0,
            "averageVehicleUtilizationPercent": 0.0,
            "executionTimeMs": 0.0,
        },
        "results": [],
        "baselineComparison": {
            "baselineValue": 0.0,
            "optimizedValue": 0.0,
            "improvementPercent": 0.0,
            "baselineUnassignedCount": 0,
            "optimizedUnassignedCount": 0,
        },
        "unassignedLocations": [],
        "explainability": [],
        "error": message,
    }


def run_engine(data: dict[str, Any]) -> dict[str, Any]:
    started_at = time.perf_counter()
    scenario_id = data.get("scenarioId") if isinstance(data, dict) else None
    try:
        validate_input(data)
    except ValueError as exc:
        result = _error_output(scenario_id, str(exc))
        result["summaryMetrics"]["executionTimeMs"] = round((time.perf_counter() - started_at) * 1000, 3)
        return result

    parameters = data["parameters"]
    vehicles = data["vehicles"]
    depot = data["depot"]
    road_factor = float(parameters["roadDistanceFactor"])
    nodes = data["nodes"]
    nodes_by_id = {node["id"]: node for node in nodes}
    allowed_nodes: list[dict[str, Any]] = []
    unassigned_reasons: dict[str, str] = {}
    available_vehicles = [vehicle for vehicle in vehicles if vehicle["available"]]
    maximum_capacity = max((float(vehicle["capacityKg"]) for vehicle in available_vehicles), default=0.0)

    for node in nodes:
        attributes = set(node.get("attributes", []))
        if not node.get("available", True):
            unassigned_reasons[node["id"]] = "The collection location is marked unavailable."
        elif (
            not parameters["allowDisruptions"]
            and node.get("disrupted", False)
        ):
            unassigned_reasons[node["id"]] = "The location is affected by a disruption that this scenario does not permit."
        elif float(node["wasteKg"]) > maximum_capacity + 1e-9:
            unassigned_reasons[node["id"]] = (
                f"The {float(node['wasteKg']):g} kg load exceeds the largest available vehicle capacity "
                f"of {maximum_capacity:g} kg."
            )
        else:
            allowed_nodes.append(node)

    routes = _clarke_wright_routes(allowed_nodes, available_vehicles, depot, road_factor)
    optimized_assignment = _choose_route_assignments(
        routes, nodes_by_id, available_vehicles, depot, road_factor, data["userPriority"]
    )
    assigned_ids = {
        node_id for route in optimized_assignment.values() for node_id in route
    }
    for node in allowed_nodes:
        if node["id"] not in assigned_ids:
            unassigned_reasons[node["id"]] = (
                "The location was left out because no remaining route assignment fits the available truck capacities."
            )

    result_routes: list[dict[str, Any]] = []
    total_distance = 0.0
    collected_waste = 0.0
    utilization_total = 0.0
    utilization_vehicle_count = 0
    for vehicle in vehicles:
        route = optimized_assignment.get(vehicle["id"], [])
        schedule, distance, duration = _schedule_route(route, nodes_by_id, depot, parameters, vehicle)
        load = _route_load(route, nodes_by_id)
        capacity = float(vehicle["capacityKg"])
        utilization = (load / capacity * 100) if capacity else 0.0
        if vehicle["available"]:
            utilization_total += utilization
            utilization_vehicle_count += 1
        total_distance += distance
        collected_waste += load
        result_routes.append({
            "groupId": vehicle["id"],
            "vehicleName": vehicle["name"],
            "vehicleType": vehicle["type"],
            "available": vehicle["available"],
            "sequence": route,
            "loadUsedKg": round(load, 2),
            "loadCapacityKg": round(capacity, 2),
            "utilizationPercent": round(utilization, 2),
            "metricValue": round(distance, 3),
            "routeDistanceKm": round(distance, 3),
            "routeDurationMinutes": round(duration, 1),
            "schedule": schedule,
        })

    baseline_assignment = _input_order_baseline(optimized_assignment, nodes)
    baseline_distance = sum(
        _route_distance(route, nodes_by_id, depot, road_factor)
        for route in baseline_assignment.values()
    )
    improvement = (
        (baseline_distance - total_distance) / baseline_distance * 100
        if baseline_distance > 0
        else 0.0
    )
    total_waste = sum(float(node["wasteKg"]) for node in nodes)
    unassigned_ids = set(unassigned_reasons)
    unassigned_locations = [
        {
            "nodeId": node["id"],
            "name": node["name"],
            "wasteKg": float(node["wasteKg"]),
            "reason": unassigned_reasons[node["id"]],
        }
        for node in nodes
        if node["id"] in unassigned_ids
    ]
    explainability = []
    for index, vehicle in enumerate(vehicles):
        route = optimized_assignment.get(vehicle["id"], [])
        if not vehicle["available"]:
            explainability.append({
                "targetId": vehicle["id"],
                "reason": f"{vehicle['name']} was excluded because it is marked unavailable.",
            })
            continue
        route_disruptions = [
            nodes_by_id[node_id]["name"]
            for node_id in route
            if nodes_by_id[node_id].get("disrupted", False)
        ]
        explanation = (
            f"{vehicle['name']} collects {len(route)} locations "
            f"({float(result_routes[index]['loadUsedKg']):g} of {float(vehicle['capacityKg']):g} kg, "
            f"{float(result_routes[index]['utilizationPercent']):g}% utilization) on a "
            f"{float(result_routes[index]['routeDistanceKm']):g} km depot-to-depot route."
        )
        if route_disruptions:
            explanation += (
                " The scenario permits collection at elevated-demand locations: "
                f"{', '.join(route_disruptions)}."
            )
        explainability.append({"targetId": vehicle["id"], "reason": explanation})
    if unassigned_locations:
        explainability.extend(
            {
                "targetId": item["nodeId"],
                "reason": f"{item['name']} was not scheduled: {item['reason']}",
            }
            for item in unassigned_locations
        )
    explainability.append({
        "targetId": "baseline",
        "reason": (
            "The baseline visits the same feasible vehicle assignments in source order; "
            "the optimized plan sequences those same stops with Clarke-Wright savings and 2-opt. "
            "Keeping coverage fixed makes the distance comparison like-for-like."
        ),
    })

    return {
        "status": "success",
        "scenarioId": data["scenarioId"],
        "algorithmUsed": "Heterogeneous CVRP: Clarke-Wright Savings + 2-opt",
        "summaryMetrics": {
            "primaryScore": round((collected_waste / total_waste * 100) if total_waste else 100.0, 2),
            "totalDistanceOrCost": round(total_distance, 3),
            "unassignedCount": len(unassigned_locations),
            "assignedCount": len(assigned_ids),
            "totalWasteKg": round(total_waste, 2),
            "collectedWasteKg": round(collected_waste, 2),
            "averageVehicleUtilizationPercent": round(
                utilization_total / utilization_vehicle_count if utilization_vehicle_count else 0.0,
                2,
            ),
            "executionTimeMs": round((time.perf_counter() - started_at) * 1000, 3),
        },
        "results": result_routes,
        "baselineComparison": {
            "baselineValue": round(baseline_distance, 3),
            "optimizedValue": round(total_distance, 3),
            "improvementPercent": round(improvement, 2),
            "baselineUnassignedCount": len(unassigned_locations),
            "optimizedUnassignedCount": len(unassigned_locations),
        },
        "unassignedLocations": unassigned_locations,
        "explainability": explainability,
        "error": None,
    }

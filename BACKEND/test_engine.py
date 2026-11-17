"""Standalone Challenge 05 checks: run with `python BACKEND/test_engine.py`."""

import unittest

try:
    from .engine import haversine_km, run_engine
except ImportError:
    from engine import haversine_km, run_engine


DEPOT = {"latitude": 6.9271, "longitude": 79.8612}
ROAD_FACTOR = 1.3


def make_nodes(*, waste_kg=5):
    centers = (
        (6.927, 79.86),
        (6.88, 79.94),
        (6.95, 79.98),
    )
    location_offsets = (0.004, 0.001, 0.006, 0.0, 0.005, 0.002, 0.003)
    nodes = []
    for index in range(20):
        center_latitude, center_longitude = centers[index % len(centers)]
        offset = location_offsets[index // len(centers)] * 0.0007
        nodes.append({
            "id": f"C{index + 1:02d}",
            "name": f"Collection point {index + 1}",
            "latitude": center_latitude + offset,
            "longitude": center_longitude - offset,
            "wasteKg": waste_kg,
            "priority": 1 + index % 5,
            "attributes": [],
            "available": True,
            "disrupted": False,
        })
    return nodes


def make_payload(nodes, *, priority="cost_efficient", allow_disruptions=False, capacities=(30, 35, 40)):
    return {
        "scenarioId": "test_waste_collection",
        "userPriority": priority,
        "parameters": {
            "allowDisruptions": allow_disruptions,
            "shiftStart": "07:30",
            "serviceMinutesPerStop": 8,
            "averageSpeedKmh": 30,
            "roadDistanceFactor": ROAD_FACTOR,
        },
        "depot": DEPOT,
        "vehicles": [
            {
                "id": f"truck_{index + 1}",
                "name": f"Truck {index + 1}",
                "type": "Compactor",
                "capacityKg": capacity,
                "available": True,
            }
            for index, capacity in enumerate(capacities)
        ],
        "nodes": nodes,
    }


def expected_route_distance(route, nodes_by_id, depot):
    points = [depot, *(nodes_by_id[node_id] for node_id in route), depot]
    return ROAD_FACTOR * sum(
        haversine_km(first, second)
        for first, second in zip(points, points[1:])
    )


class WasteCollectionEngineTests(unittest.TestCase):
    def test_normal_day_routes_all_20_points_and_beats_source_order_baseline(self):
        payload = make_payload(make_nodes())
        result = run_engine(payload)

        self.assertEqual(result["status"], "success", result["error"])
        self.assertEqual(result["summaryMetrics"]["assignedCount"], 20)
        self.assertEqual(result["summaryMetrics"]["unassignedCount"], 0)
        self.assertEqual(len(result["results"]), 3)
        self.assertTrue(all(route["sequence"] for route in result["results"]))
        self.assertEqual(
            result["summaryMetrics"]["collectedWasteKg"],
            sum(node["wasteKg"] for node in payload["nodes"]),
        )

        nodes_by_id = {node["id"]: node for node in payload["nodes"]}
        input_order = {node["id"]: index for index, node in enumerate(payload["nodes"])}
        calculated_distance = 0.0
        baseline_distance = 0.0
        for route in result["results"]:
            self.assertLessEqual(route["loadUsedKg"], route["loadCapacityKg"])
            calculated = expected_route_distance(route["sequence"], nodes_by_id, DEPOT)
            self.assertAlmostEqual(route["routeDistanceKm"], calculated, places=3)
            input_order_route = sorted(route["sequence"], key=input_order.__getitem__)
            baseline_distance += expected_route_distance(input_order_route, nodes_by_id, DEPOT)
            self.assertEqual(
                [stop["nodeId"] for stop in route["schedule"]],
                route["sequence"],
            )
            calculated_distance += calculated
        self.assertAlmostEqual(
            result["summaryMetrics"]["totalDistanceOrCost"],
            calculated_distance,
            places=3,
        )
        self.assertAlmostEqual(
            result["baselineComparison"]["baselineValue"],
            baseline_distance,
            places=3,
        )
        self.assertGreater(result["baselineComparison"]["improvementPercent"], 0)
        self.assertEqual(result["baselineComparison"]["baselineUnassignedCount"], 0)

    def test_disrupted_day_respects_availability_capacity_and_schedule(self):
        nodes = make_nodes(waste_kg=8)
        nodes[0]["available"] = False
        nodes[1].update({
            "priority": 5,
            "attributes": ["overflowing", "high_priority"],
            "disrupted": True,
        })
        nodes[19].update({
            "wasteKg": 48,
            "priority": 5,
            "attributes": ["overflowing"],
            "disrupted": True,
        })
        payload = make_payload(
            nodes,
            priority="urgent",
            allow_disruptions=True,
            capacities=(24, 32, 40),
        )
        payload["vehicles"][0]["available"] = False
        result = run_engine(payload)

        self.assertEqual(result["status"], "success", result["error"])
        assigned_ids = {
            node_id
            for route in result["results"]
            for node_id in route["sequence"]
        }
        self.assertIn("C02", assigned_ids)
        self.assertNotIn("C01", assigned_ids)
        self.assertNotIn("C20", assigned_ids)
        self.assertGreater(result["summaryMetrics"]["unassignedCount"], 10)

        routes_by_id = {route["groupId"]: route for route in result["results"]}
        self.assertEqual(routes_by_id["truck_1"]["available"], False)
        self.assertEqual(routes_by_id["truck_1"]["loadUsedKg"], 0)
        nodes_by_id = {node["id"]: node for node in payload["nodes"]}
        for route in result["results"]:
            self.assertLessEqual(route["loadUsedKg"], route["loadCapacityKg"])
            self.assertAlmostEqual(
                route["routeDistanceKm"],
                expected_route_distance(route["sequence"], nodes_by_id, DEPOT),
                places=3,
            )
        self.assertTrue(any(item["nodeId"] == "C01" for item in result["unassignedLocations"]))
        self.assertEqual(
            result["baselineComparison"]["baselineUnassignedCount"],
            result["baselineComparison"]["optimizedUnassignedCount"],
        )
        oversized = next(item for item in result["unassignedLocations"] if item["nodeId"] == "C20")
        self.assertIn("exceeds the largest available vehicle capacity", oversized["reason"])
        self.assertTrue(any("elevated-demand locations" in item["reason"] for item in result["explainability"]))


if __name__ == "__main__":
    unittest.main()

"""Standalone mathematical checks: run with `python backend/test_engine.py`."""

import unittest

try:
    from .engine import haversine_km, run_engine
except ImportError:
    from engine import haversine_km, run_engine


def node(node_id, longitude, **overrides):
    value = {
        "id": node_id,
        "name": node_id,
        "latitude": 0.0,
        "longitude": longitude,
        "demandOrLoad": 1,
        "attributes": [],
    }
    value.update(overrides)
    return value


def payload(nodes, *, max_resources, capacity, allow_disruptions=False):
    return {
        "scenarioId": "test",
        "userPriority": "cost_efficient",
        "parameters": {
            "maxResources": max_resources,
            "capacityLimit": capacity,
            "allowDisruptions": allow_disruptions,
        },
        "nodes": nodes,
    }


class EngineTests(unittest.TestCase):
    def test_normal_routes_reduce_greedy_distance_and_respect_capacity(self):
        locations = [
            node("A1", 0.0),
            node("B1", 1.0),
            node("A2", 0.01),
            node("B2", 1.01),
        ]
        result = run_engine(payload(locations, max_resources=2, capacity=2))

        self.assertEqual(result["status"], "success")
        self.assertEqual(result["summaryMetrics"]["unassignedCount"], 0)
        self.assertEqual(len(result["results"]), 2)
        for route in result["results"]:
            self.assertLessEqual(route["loadUsed"], route["loadCapacity"])

        locations_by_id = {location["id"]: location for location in locations}
        optimized_distance = sum(
            haversine_km(locations_by_id[first], locations_by_id[second])
            for route in result["results"]
            for first, second in zip(route["sequence"], route["sequence"][1:])
        )
        expected_distance = haversine_km(locations[0], locations[2]) + haversine_km(
            locations[1], locations[3]
        )
        baseline_distance = haversine_km(locations[0], locations[1]) + haversine_km(
            locations[2], locations[3]
        )
        self.assertAlmostEqual(optimized_distance, expected_distance, places=6)
        self.assertAlmostEqual(
            result["baselineComparison"]["baselineValue"], baseline_distance, places=6
        )
        self.assertAlmostEqual(
            result["baselineComparison"]["improvementPercent"], 99.0, places=6
        )

    def test_disrupted_route_uses_risk_cost_and_excludes_unavailable_node(self):
        locations = [
            node("start", 0.0),
            node("hazard", 0.01, disrupted=True, risk=0.8),
            node("end", 0.02),
            node("unavailable", 0.03, available=False),
        ]
        result = run_engine(
            payload(
                locations,
                max_resources=1,
                capacity=5,
                allow_disruptions=True,
            )
        )

        self.assertEqual(result["status"], "success")
        self.assertEqual(result["summaryMetrics"]["unassignedCount"], 1)
        route = result["results"][0]
        self.assertEqual(set(route["sequence"]), {"start", "hazard", "end"})
        self.assertLessEqual(route["loadUsed"], route["loadCapacity"])

        by_id = {location["id"]: location for location in locations}
        risk = {"start": 0.0, "hazard": 0.8, "end": 0.0}
        expected_cost = sum(
            haversine_km(by_id[first], by_id[second])
            * (1 + 0.5 * (risk[first] + risk[second]) / 2)
            for first, second in zip(route["sequence"], route["sequence"][1:])
        )
        self.assertAlmostEqual(route["metricValue"], expected_cost, places=6)
        self.assertAlmostEqual(
            result["summaryMetrics"]["totalDistanceOrCost"], expected_cost, places=6
        )
        self.assertTrue(
            any("accepted despite disruption" in item["reason"]
                for item in result["explainability"])
        )


if __name__ == "__main__":
    unittest.main()

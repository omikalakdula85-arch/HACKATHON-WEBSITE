import asyncio
import unittest
from unittest.mock import patch

from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool
from fastapi import HTTPException

try:
    from . import workflows
    from .database import Base
    from .models import Report, Route, RouteStop, User, Vehicle
    from .schemas import ReportAssignment
    from .settings import DEPOT
except ImportError:
    import workflows
    from database import Base
    from models import Report, Route, RouteStop, User, Vehicle
    from schemas import ReportAssignment
    from settings import DEPOT


class ReportAssignmentTests(unittest.TestCase):
    def setUp(self) -> None:
        self.engine = create_engine(
            "sqlite://",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        Base.metadata.create_all(self.engine)
        self.db = Session(self.engine, expire_on_commit=False)
        self.admin = User(username="admin@test.local", display_name="Test Admin", role="admin")
        self.driver = User(username="driver@test.local", display_name="Test Driver", role="driver")
        self.citizen = User(username="citizen@test.local", display_name="Test Citizen", role="citizen")
        self.db.add_all((self.admin, self.driver, self.citizen))
        self.db.flush()
        self.vehicle = Vehicle(
            id="test-truck",
            name="Test Truck",
            vehicle_type="Compactor",
            capacity_kg=120,
            average_speed_kmh=30,
            available=True,
            driver_id=self.driver.id,
            current_latitude=DEPOT["latitude"],
            current_longitude=DEPOT["longitude"],
        )
        self.db.add(self.vehicle)
        self.db.flush()

    def tearDown(self) -> None:
        self.db.close()
        Base.metadata.drop_all(self.engine)
        self.engine.dispose()

    def add_report(self, *, waste_kg: float = 15) -> Report:
        report = Report(
            citizen_id=self.citizen.id,
            description="Household waste needs collection near the market.",
            address="Market entrance",
            latitude=6.928,
            longitude=79.862,
            estimated_waste_kg=waste_kg,
        )
        self.db.add(report)
        self.db.flush()
        return report

    def assign(self, report: Report) -> dict:
        with patch.object(
            workflows.llm_service,
            "generate_driver_notes",
            return_value={"text": "Separate household waste before unloading.", "source": "local_rules", "warning": ""},
        ):
            return asyncio.run(workflows.assign_report_to_driver(
                report.id,
                ReportAssignment(vehicleId=self.vehicle.id),
                self.db,
                self.admin,
            ))

    def test_assignment_creates_driver_route_and_eta(self) -> None:
        report = self.add_report()

        result = self.assign(report)

        self.assertEqual(result["report"]["status"], "Assigned")
        self.assertTrue(result["report"]["eta"])
        self.assertEqual(result["route"]["driverId"], self.driver.id)
        self.assertEqual(result["route"]["stops"][0]["reportId"], report.id)
        self.assertEqual(result["route"]["stops"][0]["sequenceNumber"], 1)

    def test_assignment_inserts_stop_into_existing_planned_route(self) -> None:
        route = Route(
            vehicle_id=self.vehicle.id,
            driver_id=self.driver.id,
            status="planned",
            current_waypoint_index=0,
            speed_multiplier=1,
            current_latitude=DEPOT["latitude"],
            current_longitude=DEPOT["longitude"],
        )
        self.db.add(route)
        self.db.flush()
        existing_stop = RouteStop(
            route_id=route.id,
            sequence_number=1,
            name="Existing collection point",
            latitude=6.9344,
            longitude=79.8428,
            waste_kg=30,
            eta="08:30",
            status="Pending",
        )
        report = self.add_report()
        self.db.add(existing_stop)
        self.db.commit()

        result = self.assign(report)

        stops = result["route"]["stops"]
        self.assertEqual(len(stops), 2)
        self.assertEqual([stop["sequenceNumber"] for stop in stops], [1, 2])
        self.assertEqual({stop["reportId"] for stop in stops if stop["reportId"]}, {report.id})
        self.assertEqual(report.status, "Assigned")
        self.assertEqual(report.eta, next(stop["eta"] for stop in stops if stop["reportId"] == report.id))

    def test_assignment_rejects_load_above_truck_capacity(self) -> None:
        report = self.add_report(waste_kg=121)

        with self.assertRaises(HTTPException) as raised:
            self.assign(report)

        self.assertEqual(raised.exception.status_code, 409)
        self.assertEqual(report.status, "Pending")
        self.assertEqual(self.db.query(Route).count(), 0)


if __name__ == "__main__":
    unittest.main()

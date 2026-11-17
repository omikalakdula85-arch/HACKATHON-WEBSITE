import random
from datetime import timedelta

try:
    from .clock import utc_now
    from .database import SessionLocal, init_db
    from .ml_model import ensure_model
    from .models import CollectionRecord, Location, User, Vehicle
    from .settings import DEPOT
except ImportError:
    from clock import utc_now
    from database import SessionLocal, init_db
    from ml_model import ensure_model
    from models import CollectionRecord, Location, User, Vehicle
    from settings import DEPOT


DEMO_USERS = (
    ("admin@demo.local", "Demo Admin", "admin"),
    ("driver1@demo.local", "Amara Perera", "driver"),
    ("driver2@demo.local", "Kasun Silva", "driver"),
    ("driver3@demo.local", "Nimali Fernando", "driver"),
    ("citizen@demo.local", "Demo Citizen", "citizen"),
)

LOCATIONS = (
    ("fort", "Colombo Fort", "Fort", 6.9344, 79.8428, 0.94, 120, 2),
    ("pettah", "Pettah Market", "Pettah", 6.9388, 79.8500, 0.98, 145, 3),
    ("borella", "Borella Junction", "Borella", 6.9140, 79.8770, 0.77, 100, 2),
    ("wellawatte", "Wellawatte Station", "Wellawatte", 6.8747, 79.8612, 0.81, 105, 3),
    ("bambalapitiya", "Bambalapitiya", "Bambalapitiya", 6.8883, 79.8560, 0.75, 100, 1),
    ("dehiwala", "Dehiwala Market", "Dehiwala", 6.8560, 79.8650, 0.82, 110, 2),
    ("nugegoda", "Nugegoda Town", "Nugegoda", 6.8708, 79.8896, 0.86, 125, 3),
    ("rajagiriya", "Rajagiriya", "Rajagiriya", 6.9093, 79.8950, 0.68, 90, 1),
    ("battaramulla", "Battaramulla", "Battaramulla", 6.9025, 79.9220, 0.61, 85, 2),
    ("kotte", "Sri Jayawardenepura Kotte", "Kotte", 6.8900, 79.9065, 0.59, 85, 2),
)

ADDITIONAL_LOCATIONS = (
    ("maradana", "Maradana Station", "Maradana", 6.9288, 79.8645, 0.82, 85, 2),
    ("narahenpita", "Narahenpita Market", "Narahenpita", 6.8966, 79.8783, 0.73, 80, 2),
    ("kotahena", "Kotahena Junction", "Kotahena", 6.9524, 79.8580, 0.84, 90, 3),
    ("dematagoda", "Dematagoda", "Dematagoda", 6.9364, 79.8788, 0.79, 80, 1),
    ("union_place", "Union Place", "Slave Island", 6.9148, 79.8565, 0.81, 90, 2),
    ("slave_island", "Slave Island Station", "Slave Island", 6.9237, 79.8501, 0.78, 85, 1),
    ("kirulapone", "Kirulapone", "Kirulapone", 6.8796, 79.8737, 0.71, 80, 3),
    ("kohuwala", "Kohuwala Junction", "Kohuwala", 6.8663, 79.8853, 0.76, 90, 2),
    ("maharagama", "Maharagama Town", "Maharagama", 6.8492, 79.9265, 0.91, 100, 3),
    ("narahenpita_hospital", "Narahenpita Hospital", "Narahenpita", 6.9011, 79.8770, 0.88, 90, 2),
)

VEHICLES = (
    ("truck_compact", "Compact Truck", "Compactor", 120, "driver1@demo.local"),
    ("truck_medium", "Medium Truck", "Compactor", 180, "driver2@demo.local"),
    ("truck_heavy", "Heavy Truck", "Heavy compactor", 240, "driver3@demo.local"),
)


def seed_database() -> None:
    init_db()
    rng = random.Random(42)
    with SessionLocal() as session:
        users_by_username = {
            user.username: user
            for user in session.query(User).all()
        }
        for username, display_name, role in DEMO_USERS:
            if username not in users_by_username:
                user = User(username=username, display_name=display_name, role=role)
                session.add(user)
                users_by_username[username] = user
        session.flush()

        for location_id, name, neighborhood, latitude, longitude, density, capacity, days in LOCATIONS + ADDITIONAL_LOCATIONS:
            existing = session.get(Location, location_id)
            if existing is None:
                session.add(Location(
                    id=location_id,
                    name=name,
                    neighborhood=neighborhood,
                    latitude=latitude,
                    longitude=longitude,
                    area_density=density,
                    bin_capacity_kg=capacity,
                    days_since_pickup=days,
                    last_collected_kg=round(capacity * rng.uniform(0.25, 0.72), 1),
                    available=True,
                ))

        for vehicle_id, name, vehicle_type, capacity, driver_username in VEHICLES:
            if session.get(Vehicle, vehicle_id) is None:
                session.add(Vehicle(
                    id=vehicle_id,
                    name=name,
                    vehicle_type=vehicle_type,
                    capacity_kg=capacity,
                    average_speed_kmh=24 + (capacity / 50),
                    available=True,
                    driver_id=users_by_username[driver_username].id,
                    current_latitude=DEPOT["latitude"],
                    current_longitude=DEPOT["longitude"],
                ))

        session.flush()
        if session.query(CollectionRecord).count() == 0:
            for location in session.query(Location).all():
                for day_offset in range(45):
                    collected_at = utc_now() - timedelta(days=day_offset)
                    baseline = location.bin_capacity_kg * (
                        0.2
                        + 0.25 * location.area_density
                        + 0.025 * min(day_offset, 10)
                    )
                    session.add(CollectionRecord(
                        location_id=location.id,
                        collected_kg=round(max(1, baseline + rng.uniform(-8, 12)), 1),
                        day_of_week=collected_at.weekday(),
                        rainfall_mm=round(rng.uniform(0, 35), 1),
                        collected_at=collected_at,
                    ))
        session.commit()

    ensure_model()


if __name__ == "__main__":
    seed_database()
    print("Seeded demo users, 20 Colombo locations, 3 trucks, collection history, and the synthetic ML model.")

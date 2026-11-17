import os
from pathlib import Path

from dotenv import load_dotenv

BACKEND_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = BACKEND_DIR.parent
load_dotenv(PROJECT_ROOT / ".env")
load_dotenv(BACKEND_DIR / ".env")

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    f"sqlite:///{(BACKEND_DIR / 'waste_management.db').as_posix()}",
)
UPLOAD_DIR = BACKEND_DIR / "uploads"
MODEL_DIR = BACKEND_DIR / "models"
MODEL_PATH = MODEL_DIR / "waste_fill_model.joblib"
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
MODEL_DIR.mkdir(parents=True, exist_ok=True)

DEPOT = {
    "id": "depot",
    "name": "Colombo collection depot",
    "latitude": 6.9271,
    "longitude": 79.8612,
}
DISPOSAL_SITE = {
    "id": "disposal",
    "name": "Colombo disposal site",
    "latitude": 6.9271,
    "longitude": 79.8612,
}

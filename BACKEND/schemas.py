from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class APIModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class DemoLoginRequest(APIModel):
    username: str = Field(min_length=3, max_length=120)


class UserView(APIModel):
    id: str
    username: str
    displayName: str
    role: Literal["admin", "driver", "citizen"]


class LoginResponse(APIModel):
    accessToken: str
    tokenType: Literal["bearer"] = "bearer"
    user: UserView
    demoOnly: bool = True


class ReportCreate(APIModel):
    description: str = Field(min_length=5, max_length=2000)
    address: str = Field(default="", max_length=240)
    latitude: float = Field(ge=-90, le=90)
    longitude: float = Field(ge=-180, le=180)
    urgency: Literal["low", "medium", "high"] = "medium"


class TriageRequest(APIModel):
    description: str = Field(min_length=5, max_length=2000)
    urgency: Literal["low", "medium", "high"] = "medium"


class VehiclePatch(APIModel):
    available: bool


class ReportAssignment(APIModel):
    vehicleId: str = Field(min_length=1, max_length=36)


class SimulationSpeed(APIModel):
    multiplier: Literal[1, 2, 5]


class DriverPosition(APIModel):
    latitude: float = Field(ge=-90, le=90, allow_inf_nan=False)
    longitude: float = Field(ge=-180, le=180, allow_inf_nan=False)

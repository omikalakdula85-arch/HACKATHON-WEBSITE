export type Role = "admin" | "driver" | "citizen";

export interface User {
  id: string;
  username: string;
  displayName: string;
  role: Role;
}

export interface Location {
  id: string;
  name: string;
  neighborhood: string;
  latitude: number;
  longitude: number;
  areaDensity: number;
  binCapacityKg: number;
  daysSincePickup: number;
  lastCollectedKg: number;
  available: boolean;
  fillLevelPercent: number;
  estimatedWasteKg: number;
  confidenceRange: [number, number];
  modelVersion: string;
}

export interface Vehicle {
  id: string;
  name: string;
  type: string;
  capacityKg: number;
  averageSpeedKmh: number;
  available: boolean;
  driverId: string | null;
  driverName: string | null;
  latitude: number;
  longitude: number;
}

export interface Report {
  id: string;
  citizenId: string;
  citizenName: string;
  description: string;
  address: string;
  latitude: number;
  longitude: number;
  urgency: "low" | "medium" | "high";
  wasteType: "Hazardous" | "Organic" | "Recyclable" | "General";
  priorityScore: number;
  estimatedWasteKg: number;
  handlingInstructions: string;
  triageSource: string;
  triageWarning: string;
  status: "Pending" | "Assigned" | "En Route" | "Collected";
  assignedRouteId: string | null;
  eta: string | null;
  photoUrl: string | null;
  createdAt: string;
}

export interface RouteStop {
  id: string;
  sequenceNumber: number;
  locationId: string | null;
  reportId: string | null;
  name: string;
  latitude: number;
  longitude: number;
  wasteKg: number;
  eta: string;
  status: "Pending" | "En Route" | "Collected";
  wasteType: string;
  urgency: string;
  description: string;
  address: string;
}

export interface Waypoint {
  type: "depot" | "stop" | "disposal";
  name: string;
  latitude: number;
  longitude: number;
  sequenceNumber?: number;
}

export interface FleetRoute {
  id: string;
  vehicleId: string;
  vehicleName: string;
  driverId: string;
  status: "planned" | "active" | "paused" | "completed" | "cancelled";
  distanceKm: number;
  durationMinutes: number;
  loadUsedKg: number;
  loadCapacityKg: number;
  utilizationPercent: number;
  currentWaypointIndex: number;
  speedMultiplier: number;
  currentPosition: { latitude: number; longitude: number };
  aiRouteNotes: string;
  aiNotesSource: string;
  createdAt: string;
  startedAt: string | null;
  completedAt: string | null;
  stops: RouteStop[];
  waypoints: Waypoint[];
}

export interface Triage {
  wasteType: string;
  urgency: "low" | "medium" | "high";
  priorityScore: number;
  estimatedWasteKg: number;
  handlingInstructions: string;
  source: string;
  warning: string;
}

export interface OverviewMetrics {
  pendingReports: number;
  assignedReports: number;
  enRouteReports: number;
  collectedReports: number;
  activeRoutes: number;
  unavailableVehicles: number;
  averagePredictedFillPercent: number;
}

export interface AdminOverview {
  metrics: OverviewMetrics;
  reports: Report[];
  vehicles: Vehicle[];
  routes: FleetRoute[];
  locations: Location[];
  llm: { provider: string; model: string; configured: boolean };
}

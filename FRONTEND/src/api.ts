import type {
  AdminOverview,
  FleetRoute,
  Location,
  Report,
  Triage,
  User,
  Vehicle,
} from "./types";

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "http://127.0.0.1:8001";
const TOKEN_KEY = "buildx-demo-token";
let accessToken = localStorage.getItem(TOKEN_KEY);

export function setAccessToken(token: string | null) {
  accessToken = token;
  if (token) localStorage.setItem(TOKEN_KEY, token);
  else localStorage.removeItem(TOKEN_KEY);
}

export function getAccessToken() {
  return accessToken;
}

async function request<T>(path: string, init: RequestInit = {}): Promise<T> {
  const headers = new Headers(init.headers);
  if (accessToken) headers.set("Authorization", `Bearer ${accessToken}`);
  if (init.body && !(init.body instanceof FormData) && !headers.has("Content-Type")) {
    headers.set("Content-Type", "application/json");
  }
  const response = await fetch(`${API_BASE_URL}${path}`, { ...init, headers });
  if (!response.ok) {
    const body: unknown = await response.json().catch(() => null);
    const detail =
      typeof body === "object" && body !== null && "detail" in body
        ? (body as { detail: unknown }).detail
        : response.statusText;
    throw new Error(
      typeof detail === "string" ? detail : JSON.stringify(detail),
    );
  }
  return response.json() as Promise<T>;
}

export async function login(username: string) {
  const result = await request<{ accessToken: string; user: User }>("/api/v1/auth/demo-login", {
    method: "POST",
    body: JSON.stringify({ username }),
  });
  setAccessToken(result.accessToken);
  return result.user;
}

export async function currentUser() {
  const result = await request<{ user: User }>("/api/v1/auth/me");
  return result.user;
}

export async function logout() {
  try {
    await request("/api/v1/auth/logout", { method: "POST" });
  } finally {
    setAccessToken(null);
  }
}

export async function getLocations() {
  const result = await request<{ locations: Location[] }>("/api/v1/locations");
  return result.locations;
}

export async function getVehicles() {
  const result = await request<{ vehicles: Vehicle[] }>("/api/v1/vehicles");
  return result.vehicles;
}

export async function getAdminOverview() {
  return request<AdminOverview>("/api/v1/admin/overview");
}

export async function getCitizenReports() {
  const result = await request<{ reports: Report[] }>("/api/v1/citizen/reports");
  return result.reports;
}

export async function getAllReports() {
  const result = await request<{ reports: Report[] }>("/api/v1/admin/reports");
  return result.reports;
}

export async function previewTriage(description: string, urgency: string) {
  return request<Triage>("/api/v1/llm/triage", {
    method: "POST",
    body: JSON.stringify({ description, urgency }),
  });
}

export async function submitReport(input: {
  description: string;
  address: string;
  latitude: number;
  longitude: number;
  urgency: string;
  photo: File | null;
}) {
  const form = new FormData();
  form.set("description", input.description);
  form.set("address", input.address);
  form.set("latitude", String(input.latitude));
  form.set("longitude", String(input.longitude));
  form.set("urgency", input.urgency);
  if (input.photo) form.set("photo", input.photo);
  return request<Report>("/api/v1/citizen/reports", { method: "POST", body: form });
}

export async function dispatchFleet() {
  return request<{
    optimization: {
      summaryMetrics: {
        totalDistanceOrCost: number;
        collectedWasteKg: number;
        unassignedCount: number;
      };
      baselineComparison: { improvementPercent: number };
    };
    routes: FleetRoute[];
    unassignedLocations: Array<{ name: string; wasteKg: number; reason: string }>;
    llmWarnings: Array<{ routeId: string; warning: string }>;
  }>("/api/v1/admin/dispatch", { method: "POST" });
}

export async function getBriefing() {
  return request<{ text: string; source: string; warning: string }>("/api/v1/llm/briefing");
}

export async function setVehicleAvailability(id: string, available: boolean) {
  return request<Vehicle>(`/api/v1/admin/vehicles/${encodeURIComponent(id)}`, {
    method: "PATCH",
    body: JSON.stringify({ available }),
  });
}

export async function assignReportToDriver(reportId: string, vehicleId: string) {
  return request<{ route: FleetRoute; report: Report }>(
    `/api/v1/admin/reports/${encodeURIComponent(reportId)}/assign`,
    {
      method: "POST",
      body: JSON.stringify({ vehicleId }),
    },
  );
}

export async function getDriverRoute() {
  const result = await request<{ route: FleetRoute | null }>("/api/v1/driver/route");
  return result.route;
}

export async function startRoute() {
  const result = await request<{ route: FleetRoute }>("/api/v1/driver/route/start", { method: "POST" });
  return result.route;
}

export async function pauseRoute() {
  const result = await request<{ route: FleetRoute }>("/api/v1/driver/route/pause", { method: "POST" });
  return result.route;
}

export async function setRouteSpeed(multiplier: number) {
  const result = await request<{ route: FleetRoute }>("/api/v1/driver/route/speed", {
    method: "POST",
    body: JSON.stringify({ multiplier }),
  });
  return result.route;
}

export async function updateRouteLocation(latitude: number, longitude: number) {
  return request("/api/v1/driver/route/location", {
    method: "POST",
    body: JSON.stringify({ latitude, longitude }),
  });
}

export async function completeStop(stopId: string) {
  const result = await request<{ route: FleetRoute }>(
    `/api/v1/driver/route/stops/${encodeURIComponent(stopId)}/complete`,
    { method: "POST" },
  );
  return result.route;
}

export async function getProtectedPhoto(photoUrl: string) {
  const headers = new Headers();
  if (accessToken) headers.set("Authorization", `Bearer ${accessToken}`);
  const response = await fetch(`${API_BASE_URL}${photoUrl}`, { headers });
  if (!response.ok) throw new Error("The report photo could not be loaded.");
  return URL.createObjectURL(await response.blob());
}

export interface OptimizationNode {
  id: string;
  name: string;
  latitude: number;
  longitude: number;
  wasteKg: number;
  priority: number;
  attributes: string[];
  available: boolean;
  disrupted: boolean;
}

export interface OptimizationVehicle {
  id: string;
  name: string;
  type: string;
  capacityKg: number;
  available: boolean;
  averageSpeedKmh?: number | null;
}

export interface OptimizationInput {
  scenarioId: string;
  userPriority: "cost_efficient" | "balanced" | "urgent";
  parameters: {
    allowDisruptions: boolean;
    shiftStart: string;
    serviceMinutesPerStop: number;
    averageSpeedKmh: number;
    roadDistanceFactor: number;
  };
  depot: {
    latitude: number;
    longitude: number;
  };
  vehicles: OptimizationVehicle[];
  nodes: OptimizationNode[];
}

export interface DemoScenario {
  scenarioId: string;
  name: string;
  description: string;
  isSimulated: boolean;
  input: OptimizationInput;
}

export interface ScenarioCatalog {
  datasetId: string;
  dataStatus: string;
  disclaimer: string;
  scenarios: DemoScenario[];
}

export interface OptimizationOutput {
  status: "success" | "error";
  scenarioId: string | null;
  algorithmUsed: string;
  summaryMetrics: {
    primaryScore: number;
    totalDistanceOrCost: number;
    unassignedCount: number;
    assignedCount: number;
    totalWasteKg: number;
    collectedWasteKg: number;
    averageVehicleUtilizationPercent: number;
    executionTimeMs: number;
  };
  results: Array<{
    groupId: string;
    vehicleName: string;
    vehicleType: string;
    available: boolean;
    sequence: string[];
    loadUsedKg: number;
    loadCapacityKg: number;
    utilizationPercent: number;
    metricValue: number;
    routeDistanceKm: number;
    routeDurationMinutes: number;
    schedule: Array<{
      nodeId: string;
      name: string;
      arrivalTime: string;
      wasteKg: number;
    }>;
  }>;
  baselineComparison: {
    baselineValue: number;
    optimizedValue: number;
    improvementPercent: number;
    baselineUnassignedCount: number;
    optimizedUnassignedCount: number;
  };
  unassignedLocations: Array<{
    nodeId: string;
    name: string;
    wasteKg: number;
    reason: string;
  }>;
  explainability: Array<{
    targetId: string;
    reason: string;
  }>;
  error: string | null;
}

const API_BASE_URL =
  process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null;
}

function isOptimizationInput(value: unknown): value is OptimizationInput {
  return (
    isRecord(value) &&
    typeof value.scenarioId === "string" &&
    isRecord(value.depot) &&
    Array.isArray(value.vehicles) &&
    Array.isArray(value.nodes) &&
    isRecord(value.parameters)
  );
}

function isScenarioCatalog(value: unknown): value is ScenarioCatalog {
  return (
    isRecord(value) &&
    typeof value.datasetId === "string" &&
    typeof value.dataStatus === "string" &&
    typeof value.disclaimer === "string" &&
    Array.isArray(value.scenarios) &&
    value.scenarios.every(
      (scenario) =>
        isRecord(scenario) &&
        typeof scenario.scenarioId === "string" &&
        typeof scenario.name === "string" &&
        typeof scenario.description === "string" &&
        typeof scenario.isSimulated === "boolean" &&
        isOptimizationInput(scenario.input),
    )
  );
}

function isOptimizationOutput(value: unknown): value is OptimizationOutput {
  if (
    !isRecord(value) ||
    !isRecord(value.summaryMetrics) ||
    !isRecord(value.baselineComparison) ||
    !Array.isArray(value.results) ||
    !Array.isArray(value.unassignedLocations) ||
    !Array.isArray(value.explainability)
  ) {
    return false;
  }
  const metrics = value.summaryMetrics;
  const comparison = value.baselineComparison;
  return (
    (value.status === "success" || value.status === "error") &&
    (typeof value.scenarioId === "string" || value.scenarioId === null) &&
    typeof value.algorithmUsed === "string" &&
    typeof metrics.primaryScore === "number" &&
    typeof metrics.totalDistanceOrCost === "number" &&
    typeof metrics.unassignedCount === "number" &&
    typeof metrics.assignedCount === "number" &&
    typeof metrics.totalWasteKg === "number" &&
    typeof metrics.collectedWasteKg === "number" &&
    typeof metrics.averageVehicleUtilizationPercent === "number" &&
    typeof metrics.executionTimeMs === "number" &&
    typeof comparison.baselineValue === "number" &&
    typeof comparison.optimizedValue === "number" &&
    typeof comparison.improvementPercent === "number" &&
    typeof comparison.baselineUnassignedCount === "number" &&
    typeof comparison.optimizedUnassignedCount === "number" &&
    value.results.every(
      (route) =>
        isRecord(route) &&
        typeof route.groupId === "string" &&
        typeof route.vehicleName === "string" &&
        typeof route.vehicleType === "string" &&
        typeof route.available === "boolean" &&
        Array.isArray(route.sequence) &&
        route.sequence.every((nodeId) => typeof nodeId === "string") &&
        typeof route.loadUsedKg === "number" &&
        typeof route.loadCapacityKg === "number" &&
        typeof route.utilizationPercent === "number" &&
        typeof route.routeDistanceKm === "number" &&
        typeof route.routeDurationMinutes === "number" &&
        Array.isArray(route.schedule),
    ) &&
    value.unassignedLocations.every(
      (location) =>
        isRecord(location) &&
        typeof location.nodeId === "string" &&
        typeof location.name === "string" &&
        typeof location.wasteKg === "number" &&
        typeof location.reason === "string",
    ) &&
    value.explainability.every(
      (item) =>
        isRecord(item) &&
        typeof item.targetId === "string" &&
        typeof item.reason === "string",
    ) &&
    (typeof value.error === "string" || value.error === null)
  );
}

async function requestJson(path: string, init?: RequestInit): Promise<unknown> {
  const response = await fetch(`${API_BASE_URL}${path}`, init);
  if (!response.ok) {
    const body: unknown = await response.json().catch(() => null);
    const detail =
      isRecord(body) && typeof body.detail === "string" ? ` ${body.detail}` : "";
    throw new Error(
      `API request failed (${response.status} ${response.statusText}).${detail}`,
    );
  }
  return response.json();
}

export async function getScenarioCatalog(): Promise<ScenarioCatalog> {
  const value = await requestJson("/api/v1/scenarios");
  if (!isScenarioCatalog(value)) {
    throw new Error("The scenario API returned an invalid response.");
  }
  return value;
}

export async function processOptimization(
  input: OptimizationInput,
): Promise<OptimizationOutput> {
  const value = await requestJson("/api/v1/process", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(input),
  });
  if (!isOptimizationOutput(value)) {
    throw new Error("The optimization API returned an invalid response.");
  }
  return value;
}

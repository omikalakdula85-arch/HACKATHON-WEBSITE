import outputContract from "../../output-contract.json";

export const USE_MOCK_DATA = true;

export interface OptimizationNode {
  id: string;
  name: string;
  latitude: number;
  longitude: number;
  demandOrLoad: number;
  attributes: string[];
}

export interface OptimizationInput {
  scenarioId: string;
  userPriority: string;
  parameters: {
    maxResources: number;
    capacityLimit: number;
    allowDisruptions: boolean;
  };
  nodes: OptimizationNode[];
}

export interface OptimizationOutput {
  status: string;
  scenarioId: string;
  algorithmUsed: string;
  summaryMetrics: {
    primaryScore: number;
    totalDistanceOrCost: number;
    unassignedCount: number;
    executionTimeMs: number;
  };
  results: Array<{
    groupId: string;
    sequence: string[];
    loadUsed: number;
    loadCapacity: number;
    metricValue: number;
  }>;
  baselineComparison: {
    baselineValue: number;
    optimizedValue: number;
    improvementPercent: number;
  };
  explainability: Array<{
    targetId: string;
    reason: string;
  }>;
  error: string | null;
}

const mockOutput: OptimizationOutput = outputContract;

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null;
}

function isOptimizationOutput(value: unknown): value is OptimizationOutput {
  if (
    !isRecord(value) ||
    !isRecord(value.summaryMetrics) ||
    !isRecord(value.baselineComparison) ||
    !Array.isArray(value.results) ||
    !Array.isArray(value.explainability)
  ) {
    return false;
  }

  return (
    typeof value.status === "string" &&
    typeof value.scenarioId === "string" &&
    typeof value.algorithmUsed === "string" &&
    typeof value.summaryMetrics.primaryScore === "number" &&
    typeof value.summaryMetrics.totalDistanceOrCost === "number" &&
    typeof value.summaryMetrics.unassignedCount === "number" &&
    typeof value.summaryMetrics.executionTimeMs === "number" &&
    typeof value.baselineComparison.baselineValue === "number" &&
    typeof value.baselineComparison.optimizedValue === "number" &&
    typeof value.baselineComparison.improvementPercent === "number" &&
    value.results.every(
      (result) =>
        isRecord(result) &&
        typeof result.groupId === "string" &&
        Array.isArray(result.sequence) &&
        result.sequence.every((nodeId) => typeof nodeId === "string") &&
        typeof result.loadUsed === "number" &&
        typeof result.loadCapacity === "number" &&
        typeof result.metricValue === "number",
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

export async function processOptimization(
  input: OptimizationInput,
): Promise<OptimizationOutput> {
  if (USE_MOCK_DATA) {
    await new Promise<void>((resolve) => setTimeout(resolve, 600));
    return { ...mockOutput, scenarioId: input.scenarioId };
  }

  const response = await fetch("http://localhost:8000/api/v1/process", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(input),
  });

  if (!response.ok) {
    throw new Error(
      `Optimization request failed (${response.status} ${response.statusText}).`,
    );
  }

  const result: unknown = await response.json();
  if (!isOptimizationOutput(result)) {
    throw new Error("The optimization API returned an invalid response.");
  }

  return result;
}

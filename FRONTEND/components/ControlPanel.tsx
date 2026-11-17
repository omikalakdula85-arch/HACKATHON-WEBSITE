"use client";

import { useState } from "react";
import { Loader2, Play } from "lucide-react";
import {
  processOptimization,
  type OptimizationInput,
  type OptimizationOutput,
} from "../services/api";

type ScenarioKey = "normal" | "disrupted";

const SCENARIOS: Record<ScenarioKey, OptimizationInput> = {
  normal: {
    scenarioId: "scenario_01_normal",
    userPriority: "cost_efficient",
    parameters: {
      maxResources: 3,
      capacityLimit: 50,
      allowDisruptions: false,
    },
    nodes: [
      {
        id: "node_01",
        name: "Location Alpha",
        latitude: 6.9271,
        longitude: 79.8612,
        demandOrLoad: 15,
        attributes: ["accessible", "high_priority"],
      },
      {
        id: "node_02",
        name: "Location Beta",
        latitude: 6.9315,
        longitude: 79.855,
        demandOrLoad: 25,
        attributes: ["restricted_access"],
      },
    ],
  },
  disrupted: {
    scenarioId: "scenario_02_disrupted_high_demand",
    userPriority: "high_priority",
    parameters: {
      maxResources: 4,
      capacityLimit: 60,
      allowDisruptions: true,
    },
    nodes: [
      {
        id: "node_01",
        name: "Location Alpha",
        latitude: 6.9271,
        longitude: 79.8612,
        demandOrLoad: 38,
        attributes: ["accessible", "high_priority", "disrupted"],
      },
      {
        id: "node_02",
        name: "Location Beta",
        latitude: 6.9315,
        longitude: 79.855,
        demandOrLoad: 42,
        attributes: ["restricted_access", "high_priority"],
      },
    ],
  },
};

function cloneScenario(scenario: OptimizationInput): OptimizationInput {
  return {
    ...scenario,
    parameters: { ...scenario.parameters },
    nodes: scenario.nodes.map((node) => ({
      ...node,
      attributes: [...node.attributes],
    })),
  };
}

export default function ControlPanel() {
  const [scenario, setScenario] = useState<ScenarioKey>("normal");
  const [maxResources, setMaxResources] = useState(
    SCENARIOS.normal.parameters.maxResources,
  );
  const [capacityLimit, setCapacityLimit] = useState(
    SCENARIOS.normal.parameters.capacityLimit,
  );
  const [userPriority, setUserPriority] = useState(
    SCENARIOS.normal.userPriority,
  );
  const [allowDisruptions, setAllowDisruptions] = useState(
    SCENARIOS.normal.parameters.allowDisruptions,
  );
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [output, setOutput] = useState<OptimizationOutput | null>(null);

  function applyScenario(nextScenario: ScenarioKey) {
    const preset = SCENARIOS[nextScenario];
    setScenario(nextScenario);
    setMaxResources(preset.parameters.maxResources);
    setCapacityLimit(preset.parameters.capacityLimit);
    setUserPriority(preset.userPriority);
    setAllowDisruptions(preset.parameters.allowDisruptions);
    setOutput(null);
    setError(null);
  }

  async function runOptimization() {
    const input = cloneScenario(SCENARIOS[scenario]);
    input.parameters.maxResources = maxResources;
    input.parameters.capacityLimit = capacityLimit;
    input.parameters.allowDisruptions = allowDisruptions;
    input.userPriority = userPriority;

    setIsLoading(true);
    setError(null);

    try {
      setOutput(await processOptimization(input));
    } catch (requestError) {
      setOutput(null);
      setError(
        requestError instanceof Error
          ? requestError.message
          : "Optimization failed. Please try again.",
      );
    } finally {
      setIsLoading(false);
    }
  }

  return (
    <section className="grid gap-6 lg:grid-cols-[minmax(280px,0.9fr)_minmax(0,1.1fr)]">
      <div className="rounded-2xl border border-slate-800 bg-slate-950 p-6 text-slate-100 shadow-xl shadow-black/20">
        <div className="mb-6">
          <p className="text-xs font-semibold uppercase tracking-[0.18em] text-emerald-400">
            BuildX 0.1
          </p>
          <h2 className="mt-2 text-2xl font-semibold">Optimization controls</h2>
          <p className="mt-2 text-sm text-slate-400">
            Choose a live scenario, tune the constraints, and run the optimizer.
          </p>
        </div>

        <fieldset>
          <legend className="mb-3 text-sm font-medium text-slate-300">
            Demo scenario
          </legend>
          <div className="grid grid-cols-2 gap-3">
            <button
              type="button"
              onClick={() => applyScenario("normal")}
              aria-pressed={scenario === "normal"}
              className={`rounded-xl border px-4 py-3 text-left transition ${
                scenario === "normal"
                  ? "border-emerald-400 bg-emerald-400/10 text-emerald-200"
                  : "border-slate-700 bg-slate-900 text-slate-300 hover:border-slate-500"
              }`}
            >
              <span className="block text-sm font-semibold">Scenario A</span>
              <span className="mt-1 block text-xs text-slate-400">Normal</span>
            </button>
            <button
              type="button"
              onClick={() => applyScenario("disrupted")}
              aria-pressed={scenario === "disrupted"}
              className={`rounded-xl border px-4 py-3 text-left transition ${
                scenario === "disrupted"
                  ? "border-amber-400 bg-amber-400/10 text-amber-200"
                  : "border-slate-700 bg-slate-900 text-slate-300 hover:border-slate-500"
              }`}
            >
              <span className="block text-sm font-semibold">Scenario B</span>
              <span className="mt-1 block text-xs text-slate-400">
                Disrupted / High Demand
              </span>
            </button>
          </div>
        </fieldset>

        <div className="mt-7 space-y-6">
          <label className="block">
            <span className="flex items-center justify-between text-sm font-medium text-slate-300">
              Max resources
              <span className="rounded-md bg-slate-900 px-2 py-1 font-mono text-emerald-300">
                {maxResources}
              </span>
            </span>
            <input
              type="range"
              min="1"
              max="12"
              step="1"
              value={maxResources}
              onChange={(event) => setMaxResources(Number(event.target.value))}
              className="mt-3 w-full accent-emerald-400"
            />
            <span className="mt-1 flex justify-between text-xs text-slate-500">
              <span>1</span>
              <span>12 resources</span>
            </span>
          </label>

          <label className="block">
            <span className="flex items-center justify-between text-sm font-medium text-slate-300">
              Capacity limit
              <span className="rounded-md bg-slate-900 px-2 py-1 font-mono text-emerald-300">
                {capacityLimit}
              </span>
            </span>
            <input
              type="range"
              min="10"
              max="200"
              step="5"
              value={capacityLimit}
              onChange={(event) => setCapacityLimit(Number(event.target.value))}
              className="mt-3 w-full accent-emerald-400"
            />
            <span className="mt-1 flex justify-between text-xs text-slate-500">
              <span>10</span>
              <span>200 capacity units</span>
            </span>
          </label>

          <label className="block">
            <span className="mb-2 block text-sm font-medium text-slate-300">
              Priority strategy
            </span>
            <select
              value={userPriority}
              onChange={(event) => setUserPriority(event.target.value)}
              className="w-full rounded-lg border border-slate-700 bg-slate-900 px-3 py-2.5 text-sm text-slate-100 outline-none focus:border-emerald-400"
            >
              <option value="cost_efficient">Cost efficient</option>
              <option value="high_priority">High priority</option>
            </select>
          </label>

          <label className="flex cursor-pointer items-center justify-between rounded-xl border border-slate-800 bg-slate-900/60 p-4">
            <span>
              <span className="block text-sm font-medium text-slate-200">
                Allow disruptions
              </span>
              <span className="mt-1 block text-xs text-slate-500">
                Include disrupted conditions in the scenario
              </span>
            </span>
            <input
              type="checkbox"
              checked={allowDisruptions}
              onChange={(event) => setAllowDisruptions(event.target.checked)}
              className="h-4 w-4 accent-emerald-400"
            />
          </label>
        </div>

        <button
          type="button"
          onClick={runOptimization}
          disabled={isLoading}
          className="mt-7 flex w-full items-center justify-center gap-2 rounded-xl bg-emerald-400 px-4 py-3 font-semibold text-slate-950 transition hover:bg-emerald-300 disabled:cursor-not-allowed disabled:opacity-70"
        >
          {isLoading ? (
            <Loader2 className="h-5 w-5 animate-spin" aria-hidden="true" />
          ) : (
            <Play className="h-4 w-4 fill-current" aria-hidden="true" />
          )}
          {isLoading ? "Optimizing..." : "Run Optimization"}
        </button>

        {isLoading && (
          <p role="status" className="mt-3 text-center text-sm text-slate-400">
            Optimizing resources and evaluating scenario constraints...
          </p>
        )}
        {error && (
          <p
            role="alert"
            className="mt-3 rounded-lg border border-rose-900/80 bg-rose-950/50 p-3 text-sm text-rose-200"
          >
            {error}
          </p>
        )}
      </div>

      <div
        aria-live="polite"
        className="min-h-72 rounded-2xl border border-slate-800 bg-slate-950 p-6 text-slate-100 shadow-xl shadow-black/20"
      >
        <div className="flex items-start justify-between gap-4">
          <div>
            <p className="text-xs font-semibold uppercase tracking-[0.18em] text-slate-500">
              Optimization output
            </p>
            <h2 className="mt-2 text-xl font-semibold">Run summary</h2>
          </div>
          {output && (
            <span className="rounded-full border border-emerald-800 bg-emerald-950/60 px-3 py-1 text-xs font-medium text-emerald-300">
              {output.status}
            </span>
          )}
        </div>

        {!output && !isLoading && !error && (
          <div className="mt-8 rounded-xl border border-dashed border-slate-800 p-6 text-center">
            <p className="text-sm text-slate-400">
              Your optimization results will appear here.
            </p>
          </div>
        )}

        {isLoading && (
          <div className="mt-8 flex items-center gap-3 rounded-xl border border-slate-800 bg-slate-900/60 p-5">
            <Loader2
              className="h-5 w-5 animate-spin text-emerald-400"
              aria-hidden="true"
            />
            <span className="text-sm text-slate-300">
              Waiting for the optimization service...
            </span>
          </div>
        )}

        {output && (
          <div className="mt-6 space-y-5">
            <p className="text-sm text-slate-400">{output.algorithmUsed}</p>
            <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
              <Metric
                label="Primary score"
                value={output.summaryMetrics.primaryScore}
              />
              <Metric
                label="Total cost"
                value={output.summaryMetrics.totalDistanceOrCost}
              />
              <Metric
                label="Unassigned"
                value={output.summaryMetrics.unassignedCount}
              />
              <Metric
                label="Runtime"
                value={`${output.summaryMetrics.executionTimeMs} ms`}
              />
            </div>
            <div>
              <h3 className="text-sm font-semibold text-slate-200">
                Resource assignments
              </h3>
              <ul className="mt-2 space-y-2">
                {output.results.map((result) => (
                  <li
                    key={result.groupId}
                    className="rounded-lg border border-slate-800 bg-slate-900/60 p-3 text-sm"
                  >
                    <div className="flex justify-between gap-3">
                      <span className="font-medium text-slate-200">
                        {result.groupId}
                      </span>
                      <span className="text-slate-400">
                        {result.loadUsed} / {result.loadCapacity} capacity
                      </span>
                    </div>
                    <p className="mt-1 text-xs text-slate-500">
                      Sequence: {result.sequence.join(" -> ")}
                    </p>
                  </li>
                ))}
              </ul>
            </div>
            {output.explainability.length > 0 && (
              <div>
                <h3 className="text-sm font-semibold text-slate-200">
                  Why this result?
                </h3>
                <ul className="mt-2 space-y-2">
                  {output.explainability.map((item, index) => (
                    <li
                      key={`${item.targetId}-${index}`}
                      className="text-sm leading-6 text-slate-400"
                    >
                      <span className="font-medium text-slate-300">
                        {item.targetId}:
                      </span>{" "}
                      {item.reason}
                    </li>
                  ))}
                </ul>
              </div>
            )}
          </div>
        )}
      </div>
    </section>
  );
}

function Metric({ label, value }: { label: string; value: string | number }) {
  return (
    <div className="rounded-xl border border-slate-800 bg-slate-900/60 p-3">
      <p className="text-xs text-slate-500">{label}</p>
      <p className="mt-1 text-lg font-semibold text-slate-100">{value}</p>
    </div>
  );
}

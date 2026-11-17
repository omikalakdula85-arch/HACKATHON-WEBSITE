"use client";

import { useEffect, useState } from "react";
import { Loader2, Play } from "lucide-react";
import {
  getScenarioCatalog,
  processOptimization,
  type OptimizationInput,
  type OptimizationOutput,
  type ScenarioCatalog,
} from "../services/api";

type ControlPanelProps = {
  onComplete: (input: OptimizationInput, output: OptimizationOutput) => void;
  onReset: () => void;
};

function cloneInput(input: OptimizationInput): OptimizationInput {
  return {
    ...input,
    parameters: { ...input.parameters },
    depot: { ...input.depot },
    vehicles: input.vehicles.map((vehicle) => ({ ...vehicle })),
    nodes: input.nodes.map((node) => ({
      ...node,
      attributes: [...node.attributes],
    })),
  };
}

export default function ControlPanel({ onComplete, onReset }: ControlPanelProps) {
  const [catalog, setCatalog] = useState<ScenarioCatalog | null>(null);
  const [catalogError, setCatalogError] = useState<string | null>(null);
  const [scenarioId, setScenarioId] = useState("");
  const [userPriority, setUserPriority] =
    useState<OptimizationInput["userPriority"]>("cost_efficient");
  const [allowDisruptions, setAllowDisruptions] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [output, setOutput] = useState<OptimizationOutput | null>(null);

  useEffect(() => {
    let active = true;
    getScenarioCatalog()
      .then((response) => {
        if (!active) return;
        setCatalog(response);
        const firstScenario = response.scenarios[0];
        if (firstScenario) {
          setScenarioId(firstScenario.scenarioId);
          setUserPriority(firstScenario.input.userPriority);
          setAllowDisruptions(firstScenario.input.parameters.allowDisruptions);
        }
      })
      .catch((requestError: unknown) => {
        if (!active) return;
        setCatalogError(
          requestError instanceof Error
            ? requestError.message
            : "Unable to load collection scenarios.",
        );
      });
    return () => {
      active = false;
    };
  }, []);

  const selectedScenario = catalog?.scenarios.find(
    (scenario) => scenario.scenarioId === scenarioId,
  );

  function applyScenario(nextScenarioId: string) {
    const scenario = catalog?.scenarios.find(
      (item) => item.scenarioId === nextScenarioId,
    );
    if (!scenario) return;
    setScenarioId(nextScenarioId);
    setUserPriority(scenario.input.userPriority);
    setAllowDisruptions(scenario.input.parameters.allowDisruptions);
    setOutput(null);
    setError(null);
    onReset();
  }

  async function runOptimization() {
    if (!selectedScenario) {
      setError("Select a scenario before running the collection planner.");
      return;
    }

    const input = cloneInput(selectedScenario.input);
    input.userPriority = userPriority;
    input.parameters.allowDisruptions = allowDisruptions;
    setIsLoading(true);
    setError(null);
    setOutput(null);
    onReset();
    try {
      const result = await processOptimization(input);
      setOutput(result);
      onComplete(input, result);
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
    <section className="space-y-5">
      <div className="rounded-2xl border border-slate-800 bg-slate-950 p-5 text-slate-100 shadow-xl shadow-black/20">
        <div className="mb-5">
          <p className="text-xs font-semibold uppercase tracking-[0.18em] text-emerald-400">
            BuildX 0.1 · Challenge 05
          </p>
          <h2 className="mt-2 text-xl font-semibold">Collection planner</h2>
          <p className="mt-2 text-sm leading-6 text-slate-400">
            Route waste collection across available trucks with different
            capacities.
          </p>
        </div>

        {catalog && (
          <fieldset>
            <legend className="mb-3 text-sm font-medium text-slate-300">
              Simulated collection day
            </legend>
            <div className="grid gap-3">
              {catalog.scenarios.map((scenario, index) => (
                <button
                  type="button"
                  key={scenario.scenarioId}
                  onClick={() => applyScenario(scenario.scenarioId)}
                  aria-pressed={scenarioId === scenario.scenarioId}
                  className={`rounded-xl border px-4 py-3 text-left transition ${
                    scenarioId === scenario.scenarioId
                      ? index === 0
                        ? "border-emerald-400 bg-emerald-400/10 text-emerald-200"
                        : "border-amber-400 bg-amber-400/10 text-amber-200"
                      : "border-slate-700 bg-slate-900 text-slate-300 hover:border-slate-500"
                  }`}
                >
                  <span className="block text-sm font-semibold">
                    {scenario.name}
                  </span>
                  <span className="mt-1 block text-xs leading-5 text-slate-400">
                    {scenario.description}
                  </span>
                </button>
              ))}
            </div>
          </fieldset>
        )}

        {selectedScenario && (
          <>
            <div className="mt-5 grid grid-cols-3 gap-2">
              {selectedScenario.input.vehicles.map((vehicle) => (
                <div
                  key={vehicle.id}
                  className="rounded-lg border border-slate-800 bg-slate-900/70 p-3"
                >
                  <p className="truncate text-xs font-medium text-slate-200">
                    {vehicle.name}
                  </p>
                  <p className="mt-1 text-lg font-semibold tabular-nums text-emerald-300">
                    {vehicle.capacityKg}
                    <span className="ml-1 text-xs font-normal text-slate-400">
                      kg
                    </span>
                  </p>
                  <p className="text-[11px] text-slate-500">{vehicle.type}</p>
                </div>
              ))}
            </div>
            <p className="mt-3 text-xs leading-5 text-slate-500">
              {selectedScenario.input.nodes.length} collection locations · Depot
              start and return · {selectedScenario.input.parameters.shiftStart}{" "}
              shift start
            </p>
          </>
        )}

        <div className="mt-5 space-y-4 border-t border-slate-800 pt-5">
          <label className="block">
            <span className="mb-2 block text-sm font-medium text-slate-300">
              Planning priority
            </span>
            <select
              value={userPriority}
              onChange={(event) => {
                const value = event.target.value;
                if (
                  value === "cost_efficient" ||
                  value === "balanced" ||
                  value === "urgent"
                ) {
                  setUserPriority(value);
                }
              }}
              className="w-full rounded-lg border border-slate-700 bg-slate-900 px-3 py-2.5 text-sm text-slate-100 outline-none focus:border-emerald-400"
            >
              <option value="cost_efficient">Minimize route distance</option>
              <option value="balanced">Balanced collection priority</option>
              <option value="urgent">Prioritize urgent locations</option>
            </select>
          </label>

          <label className="flex cursor-pointer items-center justify-between rounded-xl border border-slate-800 bg-slate-900/60 p-4">
            <span>
              <span className="block text-sm font-medium text-slate-200">
                Permit disrupted locations
              </span>
              <span className="mt-1 block text-xs text-slate-500">
                Schedule points flagged as disrupted in this scenario
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
          disabled={isLoading || !selectedScenario}
          className="mt-5 flex w-full items-center justify-center gap-2 rounded-xl bg-emerald-400 px-4 py-3 font-semibold text-slate-950 transition hover:bg-emerald-300 disabled:cursor-not-allowed disabled:opacity-70"
        >
          {isLoading ? (
            <Loader2 className="h-5 w-5 animate-spin" aria-hidden="true" />
          ) : (
            <Play className="h-4 w-4 fill-current" aria-hidden="true" />
          )}
          {isLoading ? "Optimizing routes..." : "Plan collection routes"}
        </button>

        {!catalog && !catalogError && (
          <p role="status" className="mt-3 text-center text-sm text-slate-400">
            Loading simulated collection scenarios...
          </p>
        )}
        {catalogError && (
          <p
            role="alert"
            className="mt-3 rounded-lg border border-rose-900/80 bg-rose-950/50 p-3 text-sm text-rose-200"
          >
            {catalogError}
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
        {catalog?.disclaimer && (
          <p className="mt-4 text-xs leading-5 text-slate-500">
            {catalog.disclaimer}
          </p>
        )}
      </div>

      <div className="rounded-2xl border border-slate-800 bg-slate-950 p-5 text-slate-100 shadow-xl shadow-black/20">
        <div className="flex items-start justify-between gap-4">
          <div>
            <p className="text-xs font-semibold uppercase tracking-[0.18em] text-slate-500">
              Route plan
            </p>
            <h2 className="mt-2 text-lg font-semibold">Vehicle schedules</h2>
          </div>
          {output && (
            <span
              className={`rounded-full border px-3 py-1 text-xs font-medium ${
                output.status === "success"
                  ? "border-emerald-800 bg-emerald-950/60 text-emerald-300"
                  : "border-rose-800 bg-rose-950/60 text-rose-300"
              }`}
            >
              {output.status}
            </span>
          )}
        </div>

        {!output && !isLoading && (
          <p className="mt-4 rounded-xl border border-dashed border-slate-800 p-4 text-sm text-slate-400">
            Run the planner to see truck assignments and estimated stop times.
          </p>
        )}
        {isLoading && (
          <p role="status" className="mt-4 text-sm text-slate-400">
            Calculating capacity-safe routes and stop estimates...
          </p>
        )}
        {output?.error && (
          <p role="alert" className="mt-4 text-sm text-rose-300">
            {output.error}
          </p>
        )}
        {output?.status === "success" && (
          <>
            <div className="mt-4 grid grid-cols-2 gap-2">
              <ResultMetric
                label="Waste collected"
                value={`${output.summaryMetrics.collectedWasteKg} / ${output.summaryMetrics.totalWasteKg} kg`}
              />
              <ResultMetric
                label="Estimated distance"
                value={`${output.summaryMetrics.totalDistanceOrCost} km`}
              />
            </div>
            <ul className="mt-4 space-y-3">
              {output.results.map((route) => (
                <li
                  key={route.groupId}
                  className="rounded-xl border border-slate-800 bg-slate-900/60 p-3"
                >
                  <div className="flex items-start justify-between gap-3">
                    <div>
                      <p className="text-sm font-semibold text-slate-100">
                        {route.vehicleName}
                      </p>
                      <p className="mt-1 text-xs text-slate-500">
                        {route.vehicleType}
                        {!route.available ? " · unavailable" : ""}
                      </p>
                    </div>
                    <p className="text-right text-xs text-slate-300">
                      {route.loadUsedKg} / {route.loadCapacityKg} kg
                      <span className="mt-1 block text-slate-500">
                        {route.utilizationPercent}% · {route.routeDistanceKm} km
                      </span>
                    </p>
                  </div>
                  {route.schedule.length > 0 ? (
                    <ol className="mt-3 space-y-1 border-l border-slate-700 pl-3">
                      {route.schedule.map((stop) => (
                        <li
                          key={stop.nodeId}
                          className="flex justify-between gap-2 text-xs"
                        >
                          <span className="text-slate-400">
                            {stop.arrivalTime} · {stop.name}
                          </span>
                          <span className="shrink-0 text-slate-500">
                            {stop.wasteKg} kg
                          </span>
                        </li>
                      ))}
                    </ol>
                  ) : (
                    <p className="mt-2 text-xs text-slate-500">
                      No stops assigned.
                    </p>
                  )}
                  <p className="mt-2 text-xs text-slate-500">
                    Estimated route duration: {route.routeDurationMinutes} min
                  </p>
                </li>
              ))}
            </ul>
            {output.unassignedLocations.length > 0 && (
              <div className="mt-4 rounded-xl border border-amber-900/60 bg-amber-950/20 p-3">
                <h3 className="text-sm font-semibold text-amber-200">
                  Unserviceable locations ({output.unassignedLocations.length})
                </h3>
                <ul className="mt-2 space-y-2">
                  {output.unassignedLocations.map((location) => (
                    <li
                      key={location.nodeId}
                      className="text-xs leading-5 text-amber-100/80"
                    >
                      <span className="font-medium">
                        {location.name} · {location.wasteKg} kg:
                      </span>{" "}
                      {location.reason}
                    </li>
                  ))}
                </ul>
              </div>
            )}
          </>
        )}
      </div>
    </section>
  );
}

function ResultMetric({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-lg border border-slate-800 bg-slate-900/70 p-3">
      <p className="text-xs text-slate-500">{label}</p>
      <p className="mt-1 text-sm font-semibold tabular-nums text-slate-100">
        {value}
      </p>
    </div>
  );
}

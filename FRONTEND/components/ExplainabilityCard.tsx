import type { OptimizationOutput } from "../services/api";

type SummaryMetrics = OptimizationOutput["summaryMetrics"];
type ExplainabilityItem = OptimizationOutput["explainability"][number];

type ExplainabilityCardProps = {
  output: OptimizationOutput | null;
};

const metricDefinitions: {
  key: keyof SummaryMetrics;
  label: string;
  detail: string;
}[] = [
  {
    key: "primaryScore",
    label: "Waste coverage",
    detail: "Share of total waste collected",
  },
  {
    key: "totalDistanceOrCost",
    label: "Estimated distance",
    detail: "Depot-to-depot route kilometres",
  },
  {
    key: "collectedWasteKg",
    label: "Waste collected",
    detail: "Kilograms assigned to trucks",
  },
  {
    key: "assignedCount",
    label: "Locations served",
    detail: "Collection stops on a route",
  },
  {
    key: "unassignedCount",
    label: "Unserviceable",
    detail: "Stops outside available constraints",
  },
  {
    key: "averageVehicleUtilizationPercent",
    label: "Fleet utilization",
    detail: "Average load across available trucks",
  },
  {
    key: "executionTimeMs",
    label: "Execution time",
    detail: "Algorithm runtime",
  },
];

function formatMetric(value: number, key: keyof SummaryMetrics): string {
  if (!Number.isFinite(value)) {
    return "Unavailable";
  }

  const formatted = new Intl.NumberFormat("en", {
    maximumFractionDigits: 2,
  }).format(value);

  if (key === "executionTimeMs") return `${formatted} ms`;
  if (key === "totalDistanceOrCost") return `${formatted} km`;
  if (key === "collectedWasteKg") return `${formatted} kg`;
  if (key === "primaryScore" || key === "averageVehicleUtilizationPercent") {
    return `${formatted}%`;
  }
  return formatted;
}

function formatTarget(targetId: string): string {
  return targetId === "baseline" ? "Baseline comparison" : targetId;
}

export default function ExplainabilityCard({ output }: ExplainabilityCardProps) {
  const explainability = output?.explainability ?? [];
  const summaryMetrics: SummaryMetrics | null = output?.summaryMetrics ?? null;

  return (
    <section
      aria-labelledby="explainability-heading"
      className="rounded-2xl border border-slate-800 bg-slate-900/80 p-5 shadow-xl shadow-black/10 sm:p-6"
    >
      <div className="flex flex-col gap-2 sm:flex-row sm:items-end sm:justify-between">
        <div>
          <p className="text-xs font-semibold uppercase tracking-[0.2em] text-cyan-300">
            Decision transparency
          </p>
          <h2
            id="explainability-heading"
            className="mt-2 text-xl font-semibold text-white"
          >
            Why the algorithm chose this plan
          </h2>
        </div>
        <p className="text-sm text-slate-400">
          Vehicle assignments, estimated schedules, and capacity decisions.
        </p>
      </div>

      {summaryMetrics ? (
        <dl className="mt-5 grid grid-cols-2 gap-3 lg:grid-cols-3 xl:grid-cols-4">
          {metricDefinitions.map(({ key, label, detail }) => (
            <div
              key={key}
              className="rounded-xl border border-slate-800 bg-slate-950/70 p-4"
            >
              <dt className="text-xs font-medium text-slate-400">{label}</dt>
              <dd className="mt-2 text-2xl font-semibold tabular-nums text-white">
                {formatMetric(summaryMetrics[key], key)}
              </dd>
              <p className="mt-1 text-xs text-slate-500">{detail}</p>
            </div>
          ))}
        </dl>
      ) : (
        <p className="mt-5 rounded-xl border border-dashed border-slate-700 p-4 text-sm text-slate-400">
          Run an optimization to see metrics and decision rationale.
        </p>
      )}

      {output && (
        <div className="mt-6">
          <h3 className="text-sm font-semibold text-slate-200">
            Decision rationale
          </h3>
          {explainability.length > 0 ? (
            <ol className="mt-3 space-y-3">
              {explainability.map(({ targetId, reason }, index) => (
                <li
                  key={`${targetId}-${index}`}
                  className="flex gap-3 rounded-xl border border-slate-800/80 bg-slate-950/50 p-4"
                >
                  <span
                    aria-hidden="true"
                    className="mt-0.5 flex h-7 w-7 shrink-0 items-center justify-center rounded-full bg-cyan-400/10 text-xs font-semibold text-cyan-200"
                  >
                    {String(index + 1).padStart(2, "0")}
                  </span>
                  <div className="min-w-0">
                    <p className="text-xs font-semibold uppercase tracking-wide text-cyan-200">
                      {formatTarget(targetId)}
                    </p>
                    <p className="mt-1 text-sm leading-6 text-slate-300">
                      {reason}
                    </p>
                  </div>
                </li>
              ))}
            </ol>
          ) : (
            <p className="mt-3 rounded-xl border border-dashed border-slate-700 p-4 text-sm text-slate-400">
              No decision rationale is available for this result.
            </p>
          )}
        </div>
      )}
    </section>
  );
}

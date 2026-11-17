import type { OptimizationOutput } from "../services/api";

type MetricsChartsProps = {
  comparison: OptimizationOutput["baselineComparison"] | null;
  scenarioId: string | null;
};

export default function MetricsCharts({
  comparison,
  scenarioId,
}: MetricsChartsProps) {
  if (!comparison) {
    return (
      <section className="rounded-2xl border border-slate-800 bg-slate-950 p-5 text-slate-100 shadow-xl shadow-black/20">
        <p className="text-sm text-slate-400">
          Run the planner to compare optimized stop order against the same stops in input order.
        </p>
      </section>
    );
  }

  const { baselineValue, optimizedValue, improvementPercent } = comparison;
  const maxValue = Math.max(baselineValue, optimizedValue, 0);
  const calculatedImprovement =
    baselineValue > 0 ? ((baselineValue - optimizedValue) / baselineValue) * 100 : 0;
  const displayedImprovement = Number.isFinite(improvementPercent)
    ? improvementPercent
    : calculatedImprovement;
  const isImproved = optimizedValue <= baselineValue;

  return (
    <section className="rounded-2xl border border-slate-800 bg-slate-950 p-5 text-slate-100 shadow-xl shadow-black/20">
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <p className="text-xs font-semibold uppercase tracking-[0.18em] text-indigo-400">Algorithm efficiency</p>
          <h2 className="mt-1 text-lg font-semibold text-white">Baseline comparison</h2>
          <p className="mt-1 text-sm text-slate-400">Same truck assignments and stops · estimated depot-to-depot distance</p>
        </div>
        <div
          className={`rounded-full border px-3 py-1.5 text-sm font-semibold ${
            isImproved
              ? "border-emerald-500/30 bg-emerald-500/10 text-emerald-300"
              : "border-amber-500/30 bg-amber-500/10 text-amber-300"
          }`}
        >
          {isImproved ? "↓" : "↑"} {Math.abs(displayedImprovement).toFixed(2)}%
          <span className="ml-1 font-normal text-slate-400">{isImproved ? "improvement" : "change"}</span>
        </div>
      </div>

      <div aria-label="Baseline and optimized value comparison" className="mt-7 space-y-5" role="img">
        {[
          { label: "Baseline", value: baselineValue, color: "bg-slate-500" },
          { label: "Optimized", value: optimizedValue, color: "bg-gradient-to-r from-indigo-500 to-emerald-400" },
        ].map((item) => (
          <div key={item.label}>
            <div className="mb-2 flex items-center justify-between gap-4 text-sm">
              <span className="text-slate-300">{item.label}</span>
              <span className="font-semibold tabular-nums text-white">{item.value.toFixed(2)} km</span>
            </div>
            <div className="h-3 overflow-hidden rounded-full bg-slate-800">
              <div
                className={`h-full rounded-full transition-[width] duration-700 ${item.color}`}
                style={{ width: `${maxValue > 0 ? (item.value / maxValue) * 100 : 0}%` }}
              />
            </div>
          </div>
        ))}
      </div>

      <div className="mt-6 grid grid-cols-2 gap-3 border-t border-slate-800 pt-4">
        <div>
          <p className="text-xs text-slate-500">
            {isImproved ? "Distance saved" : "Extra distance"}
          </p>
          <p className={`mt-1 text-base font-semibold tabular-nums ${isImproved ? "text-emerald-300" : "text-amber-300"}`}>
            {Math.abs(baselineValue - optimizedValue).toFixed(2)} km
          </p>
        </div>
        <div className="text-right">
          <p className="text-xs text-slate-500">Unserviceable</p>
          <p className="mt-1 truncate text-sm font-medium text-slate-300">
            Baseline {comparison.baselineUnassignedCount} · Optimized{" "}
            {comparison.optimizedUnassignedCount}
          </p>
        </div>
      </div>
      <p className="mt-3 truncate text-xs text-slate-500">Scenario: {scenarioId}</p>
    </section>
  );
}

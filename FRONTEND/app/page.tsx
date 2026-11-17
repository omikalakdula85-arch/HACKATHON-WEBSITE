import ControlPanel from "../components/ControlPanel";
import ExplainabilityCard from "../components/ExplainabilityCard";
import MapVisualizer from "../components/MapVisualizer";
import MetricsCharts from "../components/MetricsCharts";

export default function DashboardPage() {
  return (
    <main className="min-h-screen bg-slate-950 text-slate-100">
      <div className="mx-auto max-w-[1600px] px-4 py-6 sm:px-6 lg:px-8 lg:py-8">
        <header className="mb-6 flex flex-col gap-4 border-b border-slate-800 pb-6 sm:flex-row sm:items-center sm:justify-between">
          <div>
            <p className="text-xs font-semibold uppercase tracking-[0.24em] text-cyan-300">
              BuildX 0.1 · Decision support
            </p>
            <h1 className="mt-2 text-2xl font-bold tracking-tight text-white sm:text-3xl">
              Resource Allocation Dashboard
            </h1>
            <p className="mt-2 max-w-2xl text-sm leading-6 text-slate-400">
              Configure a scenario, inspect the proposed allocation, and review
              the reasoning behind the result.
            </p>
          </div>
          <span className="inline-flex w-fit items-center gap-2 rounded-full border border-amber-300/25 bg-amber-300/10 px-3 py-2 text-xs font-semibold text-amber-100">
            <span
              aria-hidden="true"
              className="h-2 w-2 rounded-full bg-amber-300"
            />
            Simulated Sri Lankan Dataset
          </span>
        </header>

        <div className="grid items-start gap-6 xl:grid-cols-[minmax(280px,0.8fr)_minmax(0,2fr)]">
          <aside
            aria-label="Scenario controls"
            className="min-w-0 rounded-2xl border border-slate-800 bg-slate-900/60 p-4 sm:p-5"
          >
            <div className="mb-4">
              <h2 className="text-lg font-semibold text-white">
                Scenario controls
              </h2>
              <p className="mt-1 text-sm text-slate-400">
                Adjust inputs and priorities for the allocation run.
              </p>
            </div>
            <ControlPanel />
          </aside>

          <section aria-label="Optimization results" className="min-w-0">
            <div className="grid gap-6 2xl:grid-cols-2">
              <div className="min-w-0 overflow-hidden rounded-2xl border border-slate-800 bg-slate-900/60 p-4 sm:p-5">
                <div className="mb-4">
                  <h2 className="text-lg font-semibold text-white">
                    Allocation map
                  </h2>
                  <p className="mt-1 text-sm text-slate-400">
                    Locations and proposed resource assignments.
                  </p>
                </div>
                <MapVisualizer />
              </div>

              <div className="min-w-0 overflow-hidden rounded-2xl border border-slate-800 bg-slate-900/60 p-4 sm:p-5">
                <div className="mb-4">
                  <h2 className="text-lg font-semibold text-white">
                    Performance metrics
                  </h2>
                  <p className="mt-1 text-sm text-slate-400">
                    Compare the optimization outcome at a glance.
                  </p>
                </div>
                <MetricsCharts />
              </div>
            </div>
          </section>

          <div className="min-w-0 xl:col-span-2">
            <ExplainabilityCard />
          </div>
        </div>
      </div>
    </main>
  );
}

"use client";

import { useState } from "react";
import type { OptimizationInput, OptimizationOutput } from "../services/api";

const VIEWBOX_WIDTH = 560;
const VIEWBOX_HEIGHT = 440;
const LONGITUDE_BOUNDS = { min: 79.82, max: 80.01 };
const LATITUDE_BOUNDS = { min: 6.82, max: 6.97 };
const routeColors = ["#34d399", "#818cf8", "#22d3ee", "#fbbf24"];

type MapVisualizerProps = {
  input: OptimizationInput | null;
  output: OptimizationOutput | null;
};

function projectCoordinates(latitude: number, longitude: number) {
  return {
    x:
      42 +
      ((longitude - LONGITUDE_BOUNDS.min) /
        (LONGITUDE_BOUNDS.max - LONGITUDE_BOUNDS.min)) *
        470,
    y:
      28 +
      ((LATITUDE_BOUNDS.max - latitude) /
        (LATITUDE_BOUNDS.max - LATITUDE_BOUNDS.min)) *
        370,
  };
}

export default function MapVisualizer({ input, output }: MapVisualizerProps) {
  const [selectedNode, setSelectedNode] = useState<string | null>(null);
  const inputNodes = input?.nodes ?? [];
  const results = output?.results ?? [];
  const routeByNode = new Map<string, (typeof results)[number]>();
  results.forEach((route) => {
    route.sequence.forEach((nodeId) => routeByNode.set(nodeId, route));
  });
  const unassignedByNode = new Map(
    (output?.unassignedLocations ?? []).map((item) => [item.nodeId, item]),
  );
  const nodes = inputNodes.map((node) => {
    const route = routeByNode.get(node.id);
    const unassigned = unassignedByNode.get(node.id);
    const routeIndex = route ? results.indexOf(route) : -1;
    return {
      ...node,
      ...projectCoordinates(node.latitude, node.longitude),
      route,
      unassigned,
      color: unassigned
        ? "#fb7185"
        : route
          ? routeColors[routeIndex % routeColors.length]
          : "#94a3b8",
    };
  });
  const depot = input?.depot
    ? projectCoordinates(input.depot.latitude, input.depot.longitude)
    : null;
  const selected = nodes.find((node) => node.id === selectedNode);

  return (
    <section className="overflow-hidden rounded-2xl border border-slate-800 bg-slate-950 text-slate-100 shadow-xl shadow-black/20">
      <header className="flex flex-wrap items-start justify-between gap-4 border-b border-slate-800 px-5 py-4">
        <div>
          <p className="text-xs font-semibold uppercase tracking-[0.18em] text-emerald-400">
            Colombo service area
          </p>
          <h2 className="mt-1 text-lg font-semibold text-white">
            Waste collection routes
          </h2>
        </div>
        <div className="rounded-full border border-slate-700 bg-slate-900 px-3 py-1 text-xs text-slate-300">
          {inputNodes.length} locations · {input?.vehicles.length ?? 0} trucks
        </div>
      </header>

      <div className="relative p-3 sm:p-5">
        <svg
          aria-label="Interactive Colombo collection map with depot, collection points, and proposed routes"
          className="h-auto w-full rounded-xl bg-slate-900"
          role="group"
          viewBox={`0 0 ${VIEWBOX_WIDTH} ${VIEWBOX_HEIGHT}`}
        >
          <defs>
            <pattern
              height="28"
              id="map-grid"
              patternUnits="userSpaceOnUse"
              width="28"
            >
              <path
                d="M 28 0 L 0 0 0 28"
                fill="none"
                stroke="#1e293b"
                strokeWidth="0.7"
              />
            </pattern>
          </defs>
          <rect fill="url(#map-grid)" height={VIEWBOX_HEIGHT} width={VIEWBOX_WIDTH} />
          <text fill="#94a3b8" fontSize="11" letterSpacing="2" x="202" y="214">
            COLOMBO SERVICE REGION
          </text>
          <text fill="#64748b" fontSize="10" x="430" y="420">
            Simulated locations
          </text>

          {output &&
            depot &&
            results.map((route, routeIndex) => {
              if (!route.sequence.length) return null;
              const routePoints = [
                depot,
                ...route.sequence.flatMap((nodeId) => {
                  const node = inputNodes.find((item) => item.id === nodeId);
                  return node
                    ? [projectCoordinates(node.latitude, node.longitude)]
                    : [];
                }),
                depot,
              ];
              return (
                <polyline
                  key={route.groupId}
                  aria-label={`${route.vehicleName} route`}
                  fill="none"
                  points={routePoints.map((point) => `${point.x},${point.y}`).join(" ")}
                  stroke={routeColors[routeIndex % routeColors.length]}
                  strokeDasharray="5 5"
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeOpacity="0.78"
                  strokeWidth="2.5"
                />
              );
            })}

          {nodes.map((node) => (
            <g
              aria-label={`${node.name}, ${node.wasteKg} kilograms, ${
                node.unassigned
                  ? "unserviceable"
                  : node.route
                    ? node.route.vehicleName
                    : "not yet planned"
              }`}
              className="cursor-pointer outline-none"
              key={node.id}
              onClick={() =>
                setSelectedNode(selectedNode === node.id ? null : node.id)
              }
              onKeyDown={(event) => {
                if (event.key === "Enter" || event.key === " ") {
                  event.preventDefault();
                  setSelectedNode(selectedNode === node.id ? null : node.id);
                }
              }}
              role="button"
              tabIndex={0}
            >
              <title>
                {`${node.name} · ${node.wasteKg} kg · ${
                  node.unassigned
                    ? "unserviceable"
                    : node.route?.vehicleName ?? "not yet planned"
                }`}
              </title>
              <circle
                cx={node.x}
                cy={node.y}
                fill={node.color}
                fillOpacity="0.2"
                r={selectedNode === node.id ? 14 : 10}
              />
              <circle
                cx={node.x}
                cy={node.y}
                fill={node.color}
                r={selectedNode === node.id ? 6 : 4.5}
                stroke="#ecfeff"
                strokeWidth="1.25"
              />
              <text
                fill="#e2e8f0"
                fontSize="8"
                fontWeight="600"
                x={node.x + 7}
                y={node.y - 6}
              >
                {node.id}
              </text>
            </g>
          ))}

          {depot && (
            <g aria-label="Collection depot" role="img">
              <title>Collection depot · routes start and return here</title>
              <path
                d={`M ${depot.x} ${depot.y - 9} L ${depot.x + 8} ${depot.y} L ${depot.x} ${depot.y + 9} L ${depot.x - 8} ${depot.y} Z`}
                fill="#f8fafc"
                stroke="#0f172a"
                strokeWidth="2"
              />
              <text
                fill="#f8fafc"
                fontSize="9"
                fontWeight="700"
                x={depot.x + 11}
                y={depot.y + 3}
              >
                DEPOT
              </text>
            </g>
          )}
        </svg>

        <div className="mt-4 flex flex-wrap gap-3 text-xs text-slate-400">
          <Legend color="#f8fafc" label="Depot" />
          {results.map((route, index) => (
            <Legend
              key={route.groupId}
              color={routeColors[index % routeColors.length]}
              label={route.vehicleName}
            />
          ))}
          {output?.unassignedLocations.length ? (
            <Legend color="#fb7185" label="Unserviceable" />
          ) : null}
          {!output && <Legend color="#94a3b8" label="Unplanned point" />}
        </div>

        {results.length > 0 && (
          <div className="mt-4 grid gap-3 sm:grid-cols-2">
            {results.map((route, index) => (
              <div
                className="rounded-xl border border-slate-800 bg-slate-900/80 p-3"
                key={route.groupId}
              >
                <div className="flex items-center justify-between gap-3">
                  <div className="flex min-w-0 items-center gap-2">
                    <span
                      className="h-2.5 w-2.5 shrink-0 rounded-full"
                      style={{
                        backgroundColor: routeColors[index % routeColors.length],
                      }}
                    />
                    <span className="truncate text-sm font-medium text-slate-200">
                      {route.vehicleName}
                    </span>
                  </div>
                  <span className="text-xs text-slate-400">
                    {route.sequence.length} stops
                  </span>
                </div>
                <div className="mt-2 flex items-center justify-between text-xs text-slate-400">
                  <span>
                    {route.loadUsedKg} / {route.loadCapacityKg} kg
                  </span>
                  <span>{route.routeDistanceKm} km</span>
                </div>
                <div className="mt-2 h-1.5 overflow-hidden rounded-full bg-slate-800">
                  <div
                    className="h-full rounded-full"
                    style={{
                      backgroundColor: routeColors[index % routeColors.length],
                      width: `${Math.min(route.utilizationPercent, 100)}%`,
                    }}
                  />
                </div>
              </div>
            ))}
          </div>
        )}

        {!input && (
          <p className="mt-4 text-center text-sm text-slate-400">
            Load a scenario to display the collection locations.
          </p>
        )}

        {selected && (
          <div className="absolute left-6 top-6 max-w-[calc(100%-3rem)] rounded-xl border border-slate-700 bg-slate-950/95 px-4 py-3 shadow-lg backdrop-blur">
            <p className="text-sm font-semibold text-white">{selected.name}</p>
            <p className="mt-1 text-xs text-slate-400">
              {selected.wasteKg} kg ·{" "}
              {selected.unassigned
                ? "Unserviceable"
                : selected.route?.vehicleName ?? "Not yet planned"}
            </p>
            {selected.unassigned && (
              <p className="mt-2 max-w-sm text-xs leading-5 text-rose-200">
                {selected.unassigned.reason}
              </p>
            )}
            <button
              className="mt-2 text-xs font-medium text-emerald-400 hover:text-emerald-300"
              onClick={() => setSelectedNode(null)}
              type="button"
            >
              Close details
            </button>
          </div>
        )}
      </div>
    </section>
  );
}

function Legend({ color, label }: { color: string; label: string }) {
  return (
    <span className="inline-flex items-center gap-1.5">
      <span
        aria-hidden="true"
        className="h-2.5 w-2.5 rounded-full"
        style={{ backgroundColor: color }}
      />
      {label}
    </span>
  );
}

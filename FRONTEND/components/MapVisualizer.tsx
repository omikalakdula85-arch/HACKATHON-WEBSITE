"use client";

import { useState } from "react";
import outputData from "../../output-contract.json";
import inputData from "../mock_input.json";

const VIEWBOX_WIDTH = 560;
const VIEWBOX_HEIGHT = 460;
const LONGITUDE_BOUNDS = { min: 79.1, max: 82.3 };
const LATITUDE_BOUNDS = { min: 5.8, max: 10.1 };

const routeColors = ["#34d399", "#818cf8", "#22d3ee", "#fbbf24"];

function projectCoordinates(latitude: number, longitude: number) {
  return {
    x: 90 + ((longitude - LONGITUDE_BOUNDS.min) / (LONGITUDE_BOUNDS.max - LONGITUDE_BOUNDS.min)) * 370,
    y: 30 + ((LATITUDE_BOUNDS.max - latitude) / (LATITUDE_BOUNDS.max - LATITUDE_BOUNDS.min)) * 390,
  };
}

function getLoadState(loadUsed: number, loadCapacity: number) {
  const utilization = loadCapacity > 0 ? (loadUsed / loadCapacity) * 100 : 0;

  if (utilization >= 85) return { label: "High load", color: "#fb7185", percent: utilization };
  if (utilization >= 60) return { label: "Moderate load", color: "#fbbf24", percent: utilization };
  return { label: "Low load", color: "#34d399", percent: utilization };
}

export default function MapVisualizer() {
  const [selectedNode, setSelectedNode] = useState<string | null>(null);
  const results = outputData.results;
  const inputNodes = inputData.nodes;

  const routes = results.map((result, routeIndex) => {
    const loadState = getLoadState(result.loadUsed, result.loadCapacity);
    const points = result.sequence.map((nodeId, nodeIndex) => {
      const sourceNode = inputNodes.find((node) => node.id === nodeId);
      const latitude = sourceNode?.latitude ?? 6.9271 + nodeIndex * 0.025;
      const longitude = sourceNode?.longitude ?? 79.8612 + nodeIndex * 0.03;

      return {
        id: nodeId,
        name: sourceNode?.name ?? nodeId.replace(/_/g, " "),
        latitude,
        longitude,
        ...projectCoordinates(latitude, longitude),
      };
    });

    return {
      id: result.groupId,
      points,
      color: loadState.color,
      loadState,
      result,
      routeColor: routeColors[routeIndex % routeColors.length],
    };
  });

  const selected = routes
    .flatMap((route) => route.points.map((point) => ({ ...point, route })))
    .find((point) => `${point.route.id}:${point.id}` === selectedNode);

  return (
    <section className="overflow-hidden rounded-2xl border border-slate-800 bg-slate-950 text-slate-100 shadow-xl shadow-black/20">
      <header className="flex flex-wrap items-start justify-between gap-4 border-b border-slate-800 px-5 py-4">
        <div>
          <p className="text-xs font-semibold uppercase tracking-[0.18em] text-emerald-400">Sri Lanka · live routes</p>
          <h2 className="mt-1 text-lg font-semibold text-white">Resource network</h2>
        </div>
        <div className="rounded-full border border-slate-700 bg-slate-900 px-3 py-1 text-xs text-slate-300">
          {routes.length} {routes.length === 1 ? "resource" : "resources"} · {routes.reduce((count, route) => count + route.points.length, 0)} stops
        </div>
      </header>

      <div className="relative p-3 sm:p-5">
        <svg
          aria-label="Interactive route map centered on Sri Lanka"
          className="h-auto w-full rounded-xl bg-slate-900"
          role="group"
          viewBox={`0 0 ${VIEWBOX_WIDTH} ${VIEWBOX_HEIGHT}`}
        >
          <defs>
            <pattern height="32" id="map-grid" patternUnits="userSpaceOnUse" width="32">
              <path d="M 32 0 L 0 0 0 32" fill="none" stroke="#1e293b" strokeWidth="0.7" />
            </pattern>
            <linearGradient id="island-fill" x1="0" x2="1" y1="0" y2="1">
              <stop offset="0%" stopColor="#0f766e" stopOpacity="0.38" />
              <stop offset="100%" stopColor="#312e81" stopOpacity="0.32" />
            </linearGradient>
          </defs>
          <rect fill="url(#map-grid)" height={VIEWBOX_HEIGHT} width={VIEWBOX_WIDTH} />
          <path
            d="M288 27 C270 43 257 59 251 81 C244 103 230 117 228 139 C225 162 212 180 207 204 C202 229 188 249 182 273 C176 297 161 319 164 342 C167 365 182 383 196 401 C208 417 224 432 245 439 C265 446 280 429 292 413 C307 393 325 380 333 356 C340 335 355 320 361 296 C366 275 379 254 378 231 C377 209 363 191 364 169 C365 147 350 129 350 107 C350 86 337 69 326 53 C316 39 302 29 288 27 Z"
            fill="url(#island-fill)"
            stroke="#2dd4bf"
            strokeOpacity="0.45"
            strokeWidth="1.5"
          />
          <text fill="#94a3b8" fontSize="11" letterSpacing="2" x="262" y="244">
            SRI LANKA
          </text>
          <text fill="#64748b" fontSize="10" x="110" y="428">
            Indian Ocean
          </text>

          {routes.map((route) => (
            <g key={route.id}>
              {route.points.length > 1 && (
                <polyline
                  fill="none"
                  points={route.points.map((point) => `${point.x},${point.y}`).join(" ")}
                  stroke={route.routeColor}
                  strokeDasharray="5 5"
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeOpacity="0.9"
                  strokeWidth="2.5"
                />
              )}
              {route.points.map((point, index) => {
                const key = `${route.id}:${point.id}`;
                const isSelected = selectedNode === key;

                return (
                  <g
                    aria-label={`${point.name}, ${route.id}, ${route.loadState.label}`}
                    className="cursor-pointer outline-none"
                    key={key}
                    onClick={() => setSelectedNode(isSelected ? null : key)}
                    onKeyDown={(event) => {
                      if (event.key === "Enter" || event.key === " ") {
                        event.preventDefault();
                        setSelectedNode(isSelected ? null : key);
                      }
                    }}
                    role="button"
                    tabIndex={0}
                  >
                    <title>{`${point.name} · ${route.id} · ${route.loadState.label}`}</title>
                    <circle cx={point.x} cy={point.y} fill={route.color} fillOpacity="0.2" r={isSelected ? 15 : 12} />
                    <circle
                      cx={point.x}
                      cy={point.y}
                      fill={route.color}
                      r={isSelected ? 6 : 5}
                      stroke="#ecfeff"
                      strokeWidth="1.5"
                    />
                    <text
                      fill="#e2e8f0"
                      fontSize="10"
                      fontWeight="600"
                      x={point.x + 10}
                      y={point.y - 9 - (index % 2) * 12}
                    >
                      {point.id.replace(/_/g, "-")}
                    </text>
                  </g>
                );
              })}
            </g>
          ))}
        </svg>

        <div className="mt-4 grid gap-3 sm:grid-cols-2">
          {routes.map((route) => (
            <div className="rounded-xl border border-slate-800 bg-slate-900/80 p-3" key={route.id}>
              <div className="flex items-center justify-between gap-3">
                <div className="flex min-w-0 items-center gap-2">
                  <span className="h-2.5 w-2.5 shrink-0 rounded-full" style={{ backgroundColor: route.color }} />
                  <span className="truncate text-sm font-medium text-slate-200">{route.id}</span>
                </div>
                <span className="text-xs font-medium" style={{ color: route.color }}>
                  {route.loadState.label}
                </span>
              </div>
              <div className="mt-2 flex items-center justify-between text-xs text-slate-400">
                <span>Load {route.result.loadUsed} / {route.result.loadCapacity}</span>
                <span>{Math.round(route.loadState.percent)}%</span>
              </div>
              <div className="mt-2 h-1.5 overflow-hidden rounded-full bg-slate-800">
                <div
                  className="h-full rounded-full"
                  style={{ backgroundColor: route.color, width: `${Math.min(route.loadState.percent, 100)}%` }}
                />
              </div>
            </div>
          ))}
        </div>

        {selected && (
          <div className="absolute left-6 top-6 max-w-[calc(100%-3rem)] rounded-xl border border-slate-700 bg-slate-950/95 px-4 py-3 shadow-lg backdrop-blur">
            <p className="text-sm font-semibold text-white">{selected.name}</p>
            <p className="mt-1 text-xs text-slate-400">
              {selected.route.id} · {selected.latitude.toFixed(4)}, {selected.longitude.toFixed(4)}
            </p>
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

# BuildX Resource Allocation Dashboard

## 1. Project Name

**Sri Lankan Resource Allocation Optimizer** (working title; confirm the official project name with the team before submission).

## 2. Team ID

The Team ID was not included in the repository materials. Add the registered BuildX Team ID here before submission.

## 3. Problem

Resource allocation and route planning must balance competing priorities such as travel distance or cost, resource capacity, and service demand. The current project contract models this as allocating locations to available resources while respecting capacity constraints.

## 4. Solution

The prototype is designed to let a user configure a scenario and review an optimized allocation on a dashboard. The output contract identifies a **Weighted Multi-Criteria Optimization** algorithm and includes resource assignments, summary metrics, a baseline comparison, and human-readable decision rationale. The frontend presents the controls, map, charts, and explainability together so a judge can inspect both the result and why it was chosen.

The algorithm and live API are not present in the current repository snapshot; the contract describes the intended input and output rather than proving a live run.

## 5. Tech Stack

- **Frontend (planned):** Next.js, React, and Tailwind CSS.
- **Backend (planned):** Python with FastAPI.
- **Data (planned):** Reproducible JSON fixtures and/or SQLite.
- **Optimization:** Weighted multi-criteria resource allocation, as identified by the output contract.

The repository does not yet include dependency manifests or application source for these layers.

## 6. Architecture

The intended flow is:

1. A user configures scenario parameters in the frontend.
2. The backend validates the input contract and runs the allocation algorithm.
3. The backend returns results following `output-contract.json`.
4. The dashboard renders the map and performance metrics alongside the explanation entries and summary metrics.

The repository currently contains the input/output contracts and scaffold context. The dashboard expects teammate components named `ControlPanel`, `MapVisualizer`, and `MetricsCharts`; these components and the backend integration are not included in this checkout yet.

## 7. Installation

There is no verified installation command yet: this repository snapshot has no frontend `package.json`, backend dependency file, or application entry point. Install steps should be added once those project files are checked in, rather than relying on unverified commands.

## 8. Execution

The application cannot currently be launched from this snapshot because its frontend and backend implementations and run scripts are not present. Once those are added, document the exact frontend and backend commands here and verify them from a clean checkout.

## 9. Dataset / API Information

- The demo is labeled **Simulated Sri Lankan Dataset**.
- `input-contract.json` describes two simulated locations with Colombo-area coordinates, demand/load values, attributes, and scenario parameters.
- `output-contract.json` describes a sample resource assignment, score, distance-or-cost metric, unassigned count, execution time, baseline comparison, and explanation text.
- No live external API or real-world dataset is configured. The sample values are contract fixtures and must not be presented as measured field results.

## 10. Known Limitations

- The official project name and Team ID still need confirmation.
- The teammate control, map, and chart widgets, backend implementation, API integration, dependency manifests, and run scripts are absent from this repository snapshot.
- The available contract example contains only two simulated locations and one resource assignment; it is not evidence of performance on a real or representative Sri Lankan dataset.
- The output contract's runtime and improvement values are sample values, not independently benchmarked measurements.
- The dashboard currently assumes the teammate components export default React components from `frontend/components`.

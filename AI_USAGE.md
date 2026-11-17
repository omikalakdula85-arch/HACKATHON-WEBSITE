# AI Usage Disclosure

## Tools Used

- **Copilot SDK in VS Code:** Used in this session to draft the dashboard page, the explainability card, and this disclosure and README. No other AI tools were reported in this session; teammates should add any tools they used before submission.

## AI-Assisted Work

- Added the responsive dashboard composition and the simulated-dataset badge in `FRONTEND/app/page.tsx`.
- Added rendering of the output contract's summary metrics and per-target decision rationale in `FRONTEND/components/ExplainabilityCard.tsx`.
- Drafted project documentation from the repository's input/output contracts and architecture notes. Unknown team metadata and missing runtime setup are explicitly identified rather than invented.
- The dashboard references the teammate components `ControlPanel`, `MapVisualizer`, and `MetricsCharts`; those files were not present in the checkout used for this work.

## Verification

- The output contract was inspected to align the explainability component with its `summaryMetrics` and `explainability` fields.
- The input contract was inspected to describe the simulated locations and scenario accurately.
- A runnable frontend build or test could not be performed: this checkout has no frontend package manifest and does not contain the three imported teammate components. Verify the imports, component props/exports, and a production build after those files and the frontend setup are available.
- The project team remains responsible for reviewing the generated code, confirming project identity, integrating the teammate components, and validating the full application before submission.

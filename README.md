# Loopline · BuildX Challenge 05

Loopline is a runnable Smart Waste & Fleet Management demo for Colombo. It gives citizens a collection-report workflow, drivers an ordered route manifest with a live route simulator, and city administrators a fleet command centre.

All seeded collection data and map points are simulated. The application is not connected to a municipal system, emergency service, live traffic feed, or road directions provider.

## What is included

- **Citizen workspace:** submit a waste report with map pin, optional address and photo; preview report triage; follow `Pending → Assigned → En Route → Collected` status and route ETA.
- **Driver workspace:** see assigned stops in visit order, start/pause/resume the route, choose 1x/2x/5x simulation speed, and update stop status as the truck reaches each point.
- **Admin workspace:** review reports, locations, predicted fill, vehicle availability and utilization; optimize and dispatch the fleet; inspect unserviceable stops and distance comparison; request an operations briefing.
- **Routing engine:** capacity-constrained vehicle routing with Clarke–Wright savings and 2-opt sequencing, schedule estimates, and a like-for-like input-order baseline.
- **Traditional ML:** a seeded synthetic-data `RandomForestRegressor` predicts waste-bin fill and estimated kilograms.
- **LLM integration:** optional Groq/OpenAI-compatible chat-completions API for report triage and operational notes. Without a key, explicitly labelled local rules generate triage and briefing text.
- **Persistence:** SQLite stores demo users/sessions, collection locations, vehicles, reports, routes, ordered stops, collection history and simulation events. SQLAlchemy creates the schema automatically.

## Run locally

Requirements: Python 3.10+ and Node.js 20.9+.

1. Copy `.env.example` to `.env`. The default SQLite database and browser API URL work locally. For cloud triage, set `LLM_API_KEY` in `.env`; keep the key server-side.
2. Install backend dependencies and start FastAPI from the repository root:

   ```sh
   python3 -m venv BACKEND/venv
   BACKEND/venv/bin/python -m pip install -r BACKEND/requirements.txt
   BACKEND/venv/bin/python -m uvicorn BACKEND.main:app --reload --host 127.0.0.1 --port 8001
   ```

   The API startup creates the database, seeds demo accounts, 20 Colombo collection locations (including 10 key named sites and 10 additional neighbourhood points), 3 trucks with different capacities, 900 synthetic collection-history records, and the model weights. To seed manually:

   ```sh
   BACKEND/venv/bin/python -m BACKEND.seed
   ```

3. In a second terminal:

   ```sh
   cd FRONTEND
   npm install
   npm run dev
   ```

4. Open [http://localhost:5173](http://localhost:5173). FastAPI docs are at [http://localhost:8001/docs](http://localhost:8001/docs).

Use `VITE_API_BASE_URL` in the root `.env` if the API runs at a different address. `FRONTEND_ORIGINS` controls allowed browser origins.

## Deploy with persistent storage

The suggested deployment uses Vercel for the Vite frontend, Render for FastAPI, and Supabase for PostgreSQL and private report-photo storage. The Render Blueprint is in [render.yaml](./render.yaml).

1. Create a Supabase project. In Storage, create a **private** bucket named `report-photos`. Copy the project URL, service-role key, and PostgreSQL connection string (use the session pooler connection string if the Render host cannot reach the direct database address).
2. Push this repository to GitHub and create a Render Blueprint from it. Set `DATABASE_URL`, `SUPABASE_URL`, and `SUPABASE_SERVICE_ROLE_KEY` in the Render service environment. Use the Supabase project URL and connection string; keep the service-role key secret. The API creates its tables and demo seed data at startup.
3. Import the repository into Vercel with `FRONTEND` as the root directory, `npm run build` as the build command, and `dist` as the output directory. Set `VITE_API_BASE_URL` to the Render service URL (for example, `https://loopline-api.onrender.com`).
4. Set Render's `FRONTEND_ORIGINS` to the deployed Vercel origin (for example, `https://your-project.vercel.app`) and redeploy the API.

The Supabase service-role key belongs only in Render's backend environment, never in Vercel or frontend code. Hosted report records and photos persist in Supabase; free hosting tiers may sleep or impose usage limits. The LLM key is optional, and the app uses labeled local rules when cloud triage is unavailable.

## Demo accounts

Choose a role on the login screen:

| Role | Demo account |
| --- | --- |
| Administrator | `admin@demo.local` |
| Driver | `driver1@demo.local` |
| Citizen | `citizen@demo.local` |

Two more driver accounts are seeded (`driver2@demo.local`, `driver3@demo.local`). Their vehicles have different 120 kg, 180 kg, and 240 kg capacities. The role quick-switch issues random, expiring bearer tokens stored as digests in SQLite. This is **demo-only authentication**, not production password, identity-provider, or RBAC hardening.

## API overview

All application endpoints use `/api/v1`; the role matrix and primary request/response shapes are in [api-contract.json](./api-contract.json).

- `POST /api/v1/auth/demo-login`, `GET /api/v1/auth/me`, `POST /api/v1/auth/logout`
- `GET /api/v1/locations`, `GET /api/v1/vehicles`
- `POST /api/v1/citizen/reports`, `GET /api/v1/citizen/reports`
- `GET /api/v1/admin/overview`, `GET /api/v1/admin/reports`, `POST /api/v1/admin/reports/{report_id}/assign`, `POST /api/v1/admin/dispatch`
- `GET /api/v1/ml/status`, `GET /api/v1/llm/status`, `POST /api/v1/llm/triage`, `GET /api/v1/llm/briefing`
- `GET /api/v1/driver/route`, `POST /api/v1/driver/route/start`, `/pause`, `/speed`, `/location`, and `/stops/{stop_id}/complete`

The original Challenge 05 scenario endpoints remain available at `GET /api/v1/scenarios` and `POST /api/v1/process`; their request and response schemas are [input-contract.json](./input-contract.json) and [output-contract.json](./output-contract.json).

Administrators can assign each pending citizen report to an available, driver-equipped truck from the command-centre inbox. Assignment checks remaining vehicle capacity, adds the report as a stop to the driver's planned route (or creates a route), and refreshes the ordered stops and estimated schedule. The driver sees the new stop in their manifest; the citizen sees the report status and ETA.

## Run checks

```sh
BACKEND/venv/bin/python BACKEND/test_engine.py
BACKEND/venv/bin/python BACKEND/test_services.py
BACKEND/venv/bin/python BACKEND/test_assignment.py
cd FRONTEND && npm run build
```

The routing script covers normal and disrupted cases; the service tests cover explicit offline triage and schema-invalid LLM fallback; assignment tests cover route creation, route insertion, ETA updates, and capacity rejection. The frontend build runs TypeScript checks before producing the Vite bundle.

## Limitations

- Demo role switching does not verify a password and is unsuitable for production.
- The database and generated model file are local and ignored by Git. Back up or replace them for deployment.
- The ML model is trained on generated historical patterns, not verified municipal measurements. LLM output is untrusted text and should be reviewed before operational use.
- Route distances use great-circle coordinates with a detour factor. They are estimates, not road-network navigation, traffic-aware ETAs, or dispatch guarantees.
- Photos are limited to 5 MB and common raster image formats. Keep citizen details and API keys out of screenshots and public deployments.

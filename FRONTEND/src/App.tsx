import {
  Activity,
  AlertTriangle,
  Bot,
  Check,
  CheckCircle2,
  ChevronRight,
  CircleHelp,
  Clock3,
  Cloud,
  Cpu,
  FileImage,
  Gauge,
  Leaf,
  LogOut,
  MapPin,
  Pause,
  Play,
  Recycle,
  RefreshCw,
  Route as RouteIcon,
  Send,
  ShieldCheck,
  Sparkles,
  Truck,
  Upload,
  Users,
  X,
} from "lucide-react";
import {
  type FormEvent,
  type ReactNode,
  useCallback,
  useEffect,
  useRef,
  useState,
} from "react";
import * as api from "./api";
import WasteMap from "./WasteMap";
import type {
  AdminOverview,
  FleetRoute,
  Location as CollectionLocation,
  Report,
  Role,
  Triage,
  User,
  Vehicle,
} from "./types";

const DEMO_ACCOUNTS: Array<{ role: Role; username: string; label: string }> = [
  { role: "admin", username: "admin@demo.local", label: "City operations admin" },
  { role: "driver", username: "driver1@demo.local", label: "Truck driver" },
  { role: "citizen", username: "citizen@demo.local", label: "Colombo resident" },
];

export default function App() {
  const [user, setUser] = useState<User | null>(null);
  const [initializing, setInitializing] = useState(true);
  const [loginError, setLoginError] = useState("");

  useEffect(() => {
    if (!api.getAccessToken()) {
      setInitializing(false);
      return;
    }
    api.currentUser()
      .then(setUser)
      .catch(() => api.setAccessToken(null))
      .finally(() => setInitializing(false));
  }, []);

  async function handleLogin(username: string) {
    setLoginError("");
    try {
      setUser(await api.login(username));
    } catch (error) {
      setLoginError(errorMessage(error));
    }
  }

  async function handleLogout() {
    try {
      await api.logout();
    } catch (error) {
      setLoginError(errorMessage(error));
    } finally {
      setUser(null);
    }
  }

  if (initializing) return <LoadingScreen label="Connecting to the operations system" />;
  if (!user) return <LoginScreen onLogin={handleLogin} error={loginError} />;

  return (
    <div className="app-shell">
      <aside className="sidebar">
        <div className="brand-lockup">
          <div className="brand-mark"><Recycle size={21} strokeWidth={2.2} /></div>
          <div>
            <strong>Loopline</strong>
            <span>COLOMBO OPERATIONS</span>
          </div>
        </div>
        <div className="sidebar-caption">WORKSPACE</div>
        <div className="sidebar-current">
          <span className="nav-icon"><Activity size={17} /></span>
          <span>{user.role === "admin" ? "Command centre" : user.role === "driver" ? "My route" : "My collection reports"}</span>
          <span className="active-dot" />
        </div>
        <div className="sidebar-spacer" />
        <div className="sidebar-note">
          <div className="note-icon"><ShieldCheck size={17} /></div>
          <strong>Demo environment</strong>
          <p>Locations, quantities and routes are simulated for the BuildX 0.1 challenge.</p>
        </div>
        <div className="sidebar-user">
          <div className={`avatar avatar--${user.role}`}>{user.displayName.slice(0, 1)}</div>
          <div className="sidebar-user-copy">
            <strong>{user.displayName}</strong>
            <span>{roleLabel(user.role)}</span>
          </div>
          <button className="icon-button logout-button" onClick={handleLogout} title="Sign out" aria-label="Sign out">
            <LogOut size={17} />
          </button>
        </div>
      </aside>

      <main className="main-area">
        <header className="topbar">
          <div className="breadcrumb"><span>BuildX</span><ChevronRight size={14} /><strong>{roleLabel(user.role)}</strong></div>
          <div className="topbar-right">
            <span className="live-status"><span /> System operational</span>
            <div className={`avatar avatar--small avatar--${user.role}`}>{user.displayName.slice(0, 1)}</div>
          </div>
        </header>
        {user.role === "admin" && <AdminDashboard />}
        {user.role === "citizen" && <CitizenDashboard />}
        {user.role === "driver" && <DriverDashboard />}
      </main>
    </div>
  );
}

function LoginScreen({ onLogin, error }: { onLogin: (username: string) => void; error: string }) {
  const [pending, setPending] = useState("");
  async function selectAccount(username: string) {
    setPending(username);
    await onLogin(username);
    setPending("");
  }
  return (
    <div className="login-page">
      <div className="login-aside">
        <div className="brand-lockup brand-lockup--light">
          <div className="brand-mark"><Recycle size={21} /></div>
          <div><strong>Loopline</strong><span>SMART WASTE SYSTEM</span></div>
        </div>
        <div className="login-hero">
          <div className="eyebrow"><span className="eyebrow-line" /> BUILDX · APPLIED COMPUTING</div>
          <h1>A cleaner city<br />runs on <em>good systems.</em></h1>
          <p>One shared view for community reports, collection teams and the people coordinating the city.</p>
          <div className="login-stat-row">
            <div><strong>20</strong><span>collection zones</span></div>
            <div><strong>03</strong><span>fleet vehicles</span></div>
            <div><strong>24/7</strong><span>visibility</span></div>
          </div>
        </div>
        <div className="login-foot"><span>CHALLENGE 05</span><span>COLOMBO, SRI LANKA</span></div>
      </div>
      <div className="login-panel">
        <div className="login-panel-inner">
          <div className="login-overline">WELCOME TO LOOPLINE</div>
          <h2>Choose your workspace</h2>
          <p className="muted-copy">Select a demo role to explore the application. No password is required for this prototype.</p>
          <div className="demo-role-list">
            {DEMO_ACCOUNTS.map((account) => (
              <button
                className="demo-role-button"
                key={account.role}
                onClick={() => void selectAccount(account.username)}
                disabled={Boolean(pending)}
              >
                <span className={`role-icon role-icon--${account.role}`}>
                  {account.role === "admin" ? <ShieldCheck size={20} /> : account.role === "driver" ? <Truck size={20} /> : <Users size={20} />}
                </span>
                <span className="demo-role-copy"><strong>{account.label}</strong><small>{roleLabel(account.role)} access</small></span>
                <span className="role-arrow">{pending === account.username ? <RefreshCw className="spin" size={17} /> : <ChevronRight size={18} />}</span>
              </button>
            ))}
          </div>
          {error && <div className="inline-error"><AlertTriangle size={16} />{error}</div>}
          <div className="login-disclaimer"><CircleHelp size={15} /><span>This quick-switch login is for demonstration only. It is not production authentication.</span></div>
        </div>
      </div>
    </div>
  );
}

function AdminDashboard() {
  const [overview, setOverview] = useState<AdminOverview | null>(null);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState("");
  const [error, setError] = useState("");
  const [assignmentNotice, setAssignmentNotice] = useState("");
  const [briefing, setBriefing] = useState<{ text: string; source: string; warning: string } | null>(null);
  const [dispatchResult, setDispatchResult] = useState<Awaited<ReturnType<typeof api.dispatchFleet>> | null>(null);

  const refresh = useCallback(async () => {
    setError("");
    try {
      setOverview(await api.getAdminOverview());
    } catch (caught) {
      setError(errorMessage(caught));
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { void refresh(); }, [refresh]);

  async function dispatch() {
    setBusy("dispatch");
    setError("");
    try {
      setDispatchResult(await api.dispatchFleet());
      await refresh();
    } catch (caught) {
      setError(errorMessage(caught));
    } finally {
      setBusy("");
    }
  }

  async function loadBriefing() {
    setBusy("briefing");
    setError("");
    try {
      setBriefing(await api.getBriefing());
    } catch (caught) {
      setError(errorMessage(caught));
    } finally {
      setBusy("");
    }
  }

  async function toggleVehicle(id: string, available: boolean) {
    setBusy(id);
    setError("");
    try {
      await api.setVehicleAvailability(id, available);
      await refresh();
    } catch (caught) {
      setError(errorMessage(caught));
    } finally {
      setBusy("");
    }
  }

  async function assignReport(reportId: string, vehicleId: string) {
    setBusy(reportId);
    setError("");
    setAssignmentNotice("");
    try {
      const { report, route } = await api.assignReportToDriver(reportId, vehicleId);
      setAssignmentNotice(
        `Report for ${report.address || report.description.slice(0, 40)} sent to ${route.vehicleName} (${route.stops.find((stop) => stop.reportId === report.id)?.eta ?? "schedule updated"}).`,
      );
      await refresh();
    } catch (caught) {
      setError(errorMessage(caught));
    } finally {
      setBusy("");
    }
  }

  if (loading) return <LoadingScreen label="Loading command centre" />;
  if (!overview) return <DashboardError error={error} onRetry={() => void refresh()} />;
  const { metrics } = overview;
  const highFill = overview.locations.filter((location) => location.fillLevelPercent >= 85).length;
  return (
    <div className="dashboard-content">
      <PageHeading
        kicker={`${new Intl.DateTimeFormat("en-LK", { weekday: "long", day: "numeric", month: "long", year: "numeric" }).format(new Date()).toUpperCase()} · COLOMBO`}
        title="City command centre"
        description="A clear view of collection demand, citizen reports and today's fleet."
        action={<button className="button button--primary" onClick={() => void dispatch()} disabled={busy !== ""}>
          {busy === "dispatch" ? <RefreshCw className="spin" size={16} /> : <Sparkles size={16} />}
          {busy === "dispatch" ? "Optimizing fleet..." : "Optimize & dispatch"}
        </button>}
      />
      {error && <InlineAlert message={error} onClose={() => setError("")} />}

      <section className="metric-grid">
        <MetricCard label="Awaiting collection" value={metrics.pendingReports} note="Citizen reports" icon={<MapPin size={18} />} tone="amber" />
        <MetricCard label="Predicted average fill" value={`${metrics.averagePredictedFillPercent}%`} note={`Across ${overview.locations.length} collection zones`} icon={<Gauge size={18} />} tone="green" />
        <MetricCard label="Active routes" value={metrics.activeRoutes} note={`${metrics.unavailableVehicles} trucks in service`} icon={<RouteIcon size={18} />} tone="blue" />
        <MetricCard label="Collection points" value={overview.locations.length} note={`${highFill} need priority attention`} icon={<Recycle size={18} />} tone="violet" />
      </section>

      <div className="dashboard-grid dashboard-grid--map">
        <section className="panel map-panel">
          <PanelHeading eyebrow="FLEET OVERVIEW" title="Collection network" badge="COLOMBO" />
          <div className="map-frame map-frame--admin">
            <WasteMap locations={overview.locations} reports={overview.reports} routes={overview.routes.filter((route) => route.status !== "cancelled")} vehicles={overview.vehicles} />
          </div>
          <div className="map-legend">
            <LegendDot color="green" label="Collection point" />
            <LegendDot color="amber" label="Citizen report" />
            <LegendDot color="blue" label="Active truck" />
            <span className="map-source">OpenStreetMap · illustrative locations</span>
          </div>
        </section>

        <section className="panel fleet-panel">
          <PanelHeading eyebrow="FLEET STATUS" title="Collection vehicles" />
          <div className="fleet-list">
            {overview.vehicles.map((vehicle) => (
              (() => {
                const assignedRoute = overview.routes.find((route) => route.vehicleId === vehicle.id && route.status !== "cancelled");
                const vehicleStatus = vehicle.available ? "Available" : assignedRoute?.status === "active" ? "On route" : "Unavailable";
                const utilization = assignedRoute?.utilizationPercent ?? 0;
                return (
                  <article className="vehicle-row" key={vehicle.id}>
                    <div className="vehicle-icon"><Truck size={19} /></div>
                    <div className="vehicle-detail">
                      <div className="vehicle-title"><strong>{vehicle.name}</strong><StatusPill status={vehicleStatus} /></div>
                      <span>{vehicle.type} · {assignedRoute ? `${assignedRoute.loadUsedKg}/${vehicle.capacityKg} kg planned` : `${vehicle.capacityKg} kg capacity`}</span>
                      <small>{vehicle.driverName ?? "No driver assigned"} · {utilization}% utilization</small>
                      <div className="capacity-track"><span style={{ width: `${Math.min(utilization, 100)}%` }} /></div>
                    </div>
                    <button
                      className={`availability-button${vehicle.available ? "" : " availability-button--off"}`}
                      disabled={Boolean(busy)}
                      onClick={() => void toggleVehicle(vehicle.id, !vehicle.available)}
                      title={vehicle.available ? "Mark unavailable" : "Mark available"}
                    >
                      {busy === vehicle.id ? <RefreshCw className="spin" size={15} /> : vehicle.available ? <Check size={15} /> : <X size={15} />}
                    </button>
                  </article>
                );
              })()
            ))}
          </div>
          <div className="fleet-foot"><span><span className="status-dot status-dot--green" /> {overview.vehicles.filter((vehicle) => vehicle.available).length} available</span><span>{overview.vehicles.length} vehicles total</span></div>
        </section>
      </div>

      <div className="dashboard-grid dashboard-grid--lower">
        <section className="panel reports-panel">
          <PanelHeading
            eyebrow="COMMUNITY INBOX"
            title="Citizen report assignments"
            trailing={<span className="small-count">{overview.metrics.pendingReports} awaiting dispatch</span>}
          />
          {assignmentNotice && <div className="assignment-success"><CheckCircle2 size={15} />{assignmentNotice}</div>}
          {overview.reports.length === 0 ? (
            <EmptyState icon={<CheckCircle2 size={20} />} title="All clear for now" text="New community reports will appear here." />
          ) : (
            <div className="report-table">
              {overview.reports.map((report) => (
                <ReportRow
                  key={report.id}
                  report={report}
                  showCitizen
                  vehicles={overview.vehicles}
                  routes={overview.routes}
                  busy={busy === report.id}
                  disabled={Boolean(busy)}
                  onAssign={assignReport}
                />
              ))}
            </div>
          )}
        </section>

        <section className="panel assistant-panel">
          <div className="assistant-orb"><Bot size={21} /></div>
          <PanelHeading eyebrow="OPERATIONS COPILOT" title="Daily briefing" />
          <p className="assistant-intro">A concise snapshot of service demand and operational priorities.</p>
          {briefing ? (
            <div className="briefing-result">
              <p>{briefing.text}</p>
              <SourceTag source={briefing.source} />
              {briefing.warning && <small>{briefing.warning}</small>}
            </div>
          ) : (
            <div className="briefing-placeholder"><Sparkles size={17} /><span>Generate a briefing from current fleet and report metrics.</span></div>
          )}
          <button className="button button--soft button--full" onClick={() => void loadBriefing()} disabled={Boolean(busy)}>
            {busy === "briefing" ? <RefreshCw className="spin" size={15} /> : <Bot size={16} />}
            {busy === "briefing" ? "Preparing..." : "Generate briefing"}
          </button>
          <div className="ai-status-row">
            <span><span className={`status-dot ${overview.llm.configured ? "status-dot--green" : "status-dot--amber"}`} /> {overview.llm.configured ? "Cloud LLM connected" : "Local rules active"}</span>
            <span>{overview.llm.model}</span>
          </div>
        </section>
      </div>

      {dispatchResult && (
        <section className="panel dispatch-result-panel">
          <div className="dispatch-result-title">
            <div><div className="panel-eyebrow">OPTIMIZATION COMPLETE</div><h3>Fleet plan ready</h3></div>
            <button className="icon-button" onClick={() => setDispatchResult(null)} aria-label="Dismiss dispatch results"><X size={17} /></button>
          </div>
          <div className="dispatch-stats">
            <span><strong>{dispatchResult.routes.length}</strong> routes assigned</span>
            <span><strong>{dispatchResult.optimization.summaryMetrics.collectedWasteKg} kg</strong> planned collection</span>
            <span><strong>{dispatchResult.optimization.summaryMetrics.totalDistanceOrCost} km</strong> estimated distance</span>
            <span><strong>{dispatchResult.optimization.baselineComparison.improvementPercent}%</strong> vs. source-order baseline</span>
          </div>
          {dispatchResult.unassignedLocations.length > 0 && (
            <div className="unassigned-list">
              <strong><AlertTriangle size={15} /> {dispatchResult.unassignedLocations.length} location(s) cannot be serviced</strong>
              {dispatchResult.unassignedLocations.map((item) => <span key={item.name}>{item.name}: {item.reason}</span>)}
            </div>
          )}
          {dispatchResult.llmWarnings.map((item) => <p className="muted-copy" key={item.routeId}>{item.warning}</p>)}
        </section>
      )}
      <div className="page-footnote"><Cpu size={13} /> Demand forecast: synthetic Random Forest · Routing: capacity-constrained heuristic · Results are estimates</div>
    </div>
  );
}

function CitizenDashboard() {
  const [locations, setLocations] = useState<CollectionLocation[]>([]);
  const [reports, setReports] = useState<Report[]>([]);
  const [description, setDescription] = useState("");
  const [address, setAddress] = useState("");
  const [urgency, setUrgency] = useState<"low" | "medium" | "high">("medium");
  const [coordinates, setCoordinates] = useState<{ latitude: number; longitude: number } | null>(null);
  const [photo, setPhoto] = useState<File | null>(null);
  const [photoPreview, setPhotoPreview] = useState("");
  const [triage, setTriage] = useState<Triage | null>(null);
  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [triaging, setTriaging] = useState(false);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");

  const refresh = useCallback(async () => {
    setError("");
    try {
      const [nextLocations, nextReports] = await Promise.all([api.getLocations(), api.getCitizenReports()]);
      setLocations(nextLocations);
      setReports(nextReports);
    } catch (caught) {
      setError(errorMessage(caught));
    } finally {
      setLoading(false);
    }
  }, []);
  useEffect(() => { void refresh(); }, [refresh]);

  useEffect(() => {
    if (!photo) {
      setPhotoPreview("");
      return;
    }
    const url = URL.createObjectURL(photo);
    setPhotoPreview(url);
    return () => URL.revokeObjectURL(url);
  }, [photo]);

  async function preview() {
    if (description.trim().length < 5) {
      setError("Add a few details before asking for report triage.");
      return;
    }
    setTriaging(true);
    setError("");
    try {
      setTriage(await api.previewTriage(description, urgency));
    } catch (caught) {
      setError(errorMessage(caught));
    } finally {
      setTriaging(false);
    }
  }

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError("");
    setNotice("");
    if (!coordinates) {
      setError("Choose the report location by clicking on the map.");
      return;
    }
    setSubmitting(true);
    try {
      const report = await api.submitReport({
        description,
        address,
        latitude: coordinates.latitude,
        longitude: coordinates.longitude,
        urgency,
        photo,
      });
      setReports((current) => [report, ...current]);
      setDescription("");
      setAddress("");
      setUrgency("medium");
      setCoordinates(null);
      setPhoto(null);
      setTriage(null);
      setNotice("Your report has been submitted and added to the collection queue.");
    } catch (caught) {
      setError(errorMessage(caught));
    } finally {
      setSubmitting(false);
    }
  }

  function choosePhoto(file: File | undefined) {
    if (!file) return;
    if (!["image/jpeg", "image/png", "image/webp", "image/gif"].includes(file.type)) {
      setError("Choose a JPEG, PNG, WebP or GIF image.");
      return;
    }
    if (file.size > 5 * 1024 * 1024) {
      setError("The image must be 5 MB or smaller.");
      return;
    }
    setError("");
    setPhoto(file);
  }

  if (loading) return <LoadingScreen label="Loading collection information" />;

  return (
    <div className="dashboard-content">
      <PageHeading
        kicker="COMMUNITY COLLECTION SERVICE"
        title="Make your neighbourhood cleaner."
        description="Report an overflowing bin or a waste collection issue. Your report goes straight to the city team."
        action={<button className="button button--outline" onClick={() => void refresh()}><RefreshCw size={15} /> Refresh status</button>}
      />
      {error && <InlineAlert message={error} onClose={() => setError("")} />}
      {notice && <div className="inline-success"><CheckCircle2 size={17} />{notice}<button onClick={() => setNotice("")} aria-label="Dismiss message"><X size={15} /></button></div>}

      <div className="citizen-layout">
        <section className="panel report-form-panel">
          <PanelHeading eyebrow="NEW COLLECTION REQUEST" title="Tell us what needs collecting" />
          <form onSubmit={(event) => void submit(event)} className="citizen-form">
            <label className="field-label" htmlFor="report-description">What is the issue?</label>
            <textarea
              id="report-description"
              className="text-field text-area"
              placeholder="Describe the waste, how much there is, or any nearby landmarks..."
              maxLength={2000}
              minLength={5}
              value={description}
              onChange={(event) => { setDescription(event.target.value); setTriage(null); }}
              required
            />
            <div className="field-caption">{description.length}/2000 characters</div>

            <div className="field-row">
              <label className="field-group">
                <span className="field-label">Urgency</span>
                <select className="text-field" value={urgency} onChange={(event) => { setUrgency(event.target.value as typeof urgency); setTriage(null); }}>
                  <option value="low">Low - routine pickup</option>
                  <option value="medium">Medium - please collect soon</option>
                  <option value="high">High - urgent / safety concern</option>
                </select>
              </label>
              <label className="field-group">
                <span className="field-label">Nearby landmark or address <span className="optional">(optional)</span></span>
                <input className="text-field" value={address} onChange={(event) => setAddress(event.target.value)} placeholder="Street, junction or landmark" maxLength={240} />
              </label>
            </div>

            <div className="form-section-row">
              <span className="field-label">Report location</span>
              <span className={`location-coordinate${coordinates ? " location-coordinate--set" : ""}`}>
                <MapPin size={14} /> {coordinates ? `${coordinates.latitude.toFixed(4)}, ${coordinates.longitude.toFixed(4)}` : "Choose on map"}
              </span>
            </div>
            <div className="map-frame map-frame--picker">
              <WasteMap
                locations={locations}
                reports={reports}
                selectedPoint={coordinates}
                interactive
                onChoosePoint={setCoordinates}
              />
            </div>
            <button
              className="text-button geolocate-button"
              type="button"
              onClick={() => {
                if (!navigator.geolocation) { setError("Location access is not available in this browser."); return; }
                navigator.geolocation.getCurrentPosition(
                  ({ coords: point }) => setCoordinates({ latitude: point.latitude, longitude: point.longitude }),
                  () => setError("Your location could not be read. You can still select a point on the map."),
                  { timeout: 8000 },
                );
              }}
            ><MapPin size={14} /> Use my current location</button>

            <div className="field-row photo-row">
              <div className="field-group">
                <span className="field-label">Add a photo <span className="optional">(optional · max 5 MB)</span></span>
                <label className="photo-upload">
                  <Upload size={17} />
                  <span>{photo ? photo.name : "Choose an image"}</span>
                  <input type="file" accept="image/jpeg,image/png,image/webp,image/gif" onChange={(event) => choosePhoto(event.target.files?.[0])} />
                </label>
              </div>
              {photoPreview && <img className="photo-preview" src={photoPreview} alt="Selected report preview" />}
            </div>

            {triage && <TriageCard triage={triage} />}
            <div className="form-actions">
              <button type="button" className="button button--outline" onClick={() => void preview()} disabled={triaging || description.trim().length < 5}>
                {triaging ? <RefreshCw className="spin" size={15} /> : <Bot size={16} />}
                {triaging ? "Reviewing..." : "Preview AI triage"}
              </button>
              <button type="submit" className="button button--primary" disabled={submitting}>
                {submitting ? <RefreshCw className="spin" size={15} /> : <Send size={15} />}
                {submitting ? "Sending report..." : "Submit report"}
              </button>
            </div>
            <p className="privacy-note"><ShieldCheck size={13} /> Reports and photos are visible only to you, dispatchers and your assigned collection crew.</p>
          </form>
        </section>

        <section className="panel tracking-panel">
          <PanelHeading eyebrow="YOUR ACTIVITY" title="Collection tracking" trailing={<span className="small-count">{reports.length} reports</span>} />
          {reports.length === 0 ? (
            <EmptyState icon={<MapPin size={20} />} title="No reports yet" text="When you submit a collection request, you can follow its status here." />
          ) : (
            <div className="citizen-report-list">
              {reports.map((report) => <CitizenReportCard key={report.id} report={report} />)}
            </div>
          )}
          <div className="tracking-info">
            <div className="tracking-icon"><Clock3 size={16} /></div>
            <div><strong>What happens next?</strong><p>A collection team reviews each report and adds it to an available truck route.</p></div>
          </div>
          <div className="tracking-steps">
            <span className="step-done"><CheckCircle2 size={15} /> Submitted</span><i />
            <span><Truck size={15} /> Assigned</span><i />
            <span><Recycle size={15} /> Collected</span>
          </div>
        </section>
      </div>
    </div>
  );
}

function DriverDashboard() {
  const [route, setRoute] = useState<FleetRoute | null>(null);
  const [truckPosition, setTruckPosition] = useState<{ latitude: number; longitude: number } | null>(null);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState("");
  const [error, setError] = useState("");
  const currentPositionRef = useRef(truckPosition);
  const lastPositionSend = useRef(0);
  const animationRef = useRef<number | null>(null);

  const updatePosition = useCallback((position: { latitude: number; longitude: number }) => {
    currentPositionRef.current = position;
    setTruckPosition(position);
  }, []);

  const refresh = useCallback(async () => {
    setError("");
    try {
      const next = await api.getDriverRoute();
      setRoute(next);
      if (next) updatePosition(next.currentPosition);
    } catch (caught) {
      setError(errorMessage(caught));
    } finally {
      setLoading(false);
    }
  }, [updatePosition]);

  useEffect(() => { void refresh(); }, [refresh]);

  useEffect(() => {
    if (!route || route.status !== "active") return;
    const nextStop = route.stops.find((stop) => stop.status !== "Collected");
    if (!nextStop) return;
    let cancelled = false;
    let lastRender = 0;
    const start = currentPositionRef.current ?? route.currentPosition;
    const target = { latitude: nextStop.latitude, longitude: nextStop.longitude };
    const distance = haversineKm(start, target);
    const duration = Math.max(1100, Math.min(5000, 1500 + distance * 26000)) / route.speedMultiplier;
    const startedAt = performance.now();

    const animate = (now: number) => {
      if (cancelled) return;
      const progress = Math.min(1, (now - startedAt) / duration);
      const position = {
        latitude: start.latitude + (target.latitude - start.latitude) * progress,
        longitude: start.longitude + (target.longitude - start.longitude) * progress,
      };
      if (now - lastRender > 35 || progress === 1) {
        lastRender = now;
        updatePosition(position);
      }
      if (now - lastPositionSend.current > 1400) {
        lastPositionSend.current = now;
        void api.updateRouteLocation(position.latitude, position.longitude).catch((caught: unknown) => setError(errorMessage(caught)));
      }
      if (progress < 1) {
        animationRef.current = requestAnimationFrame(animate);
        return;
      }
      void (async () => {
        try {
          await api.updateRouteLocation(target.latitude, target.longitude);
          const nextRoute = await api.completeStop(nextStop.id);
          setRoute(nextRoute);
          updatePosition(nextRoute.currentPosition);
        } catch (caught) {
          setError(errorMessage(caught));
        }
      })();
    };

    animationRef.current = requestAnimationFrame(animate);
    return () => {
      cancelled = true;
      if (animationRef.current !== null) cancelAnimationFrame(animationRef.current);
    };
  }, [route, updatePosition]);

  async function startOrResume() {
    setBusy("start");
    setError("");
    try { setRoute(await api.startRoute()); }
    catch (caught) { setError(errorMessage(caught)); }
    finally { setBusy(""); }
  }

  async function pause() {
    setBusy("pause");
    setError("");
    try { setRoute(await api.pauseRoute()); }
    catch (caught) { setError(errorMessage(caught)); }
    finally { setBusy(""); }
  }

  async function changeSpeed(speed: number) {
    setBusy("speed");
    setError("");
    try { setRoute(await api.setRouteSpeed(speed)); }
    catch (caught) { setError(errorMessage(caught)); }
    finally { setBusy(""); }
  }

  async function manuallyComplete(stopId: string) {
    setBusy(stopId);
    setError("");
    try {
      const next = await api.completeStop(stopId);
      setRoute(next);
      updatePosition(next.currentPosition);
    } catch (caught) {
      setError(errorMessage(caught));
    } finally {
      setBusy("");
    }
  }

  if (loading) return <LoadingScreen label="Loading your route manifest" />;
  if (!route) {
    return (
      <div className="dashboard-content">
        <PageHeading kicker="DRIVER WORKSPACE" title="Your route manifest" description="Your ordered collection stops and driving notes will appear here after dispatch." />
        {error && <InlineAlert message={error} onClose={() => setError("")} />}
        <section className="panel no-route-panel"><div className="no-route-icon"><Truck size={25} /></div><h3>No route assigned yet</h3><p>Ask your dispatcher to optimize and assign the fleet. Once assigned, your stops will appear in order here.</p><button className="button button--outline" onClick={() => void refresh()}><RefreshCw size={15} /> Check for route</button></section>
      </div>
    );
  }
  const completed = route.stops.filter((stop) => stop.status === "Collected").length;
  const nextStop = route.stops.find((stop) => stop.status !== "Collected");
  const progress = route.stops.length ? completed / route.stops.length * 100 : 0;

  return (
    <div className="dashboard-content">
      <PageHeading
        kicker={`DRIVER WORKSPACE · ${route.vehicleName.toUpperCase()}`}
        title="Your route manifest"
        description="Follow the ordered stops. The simulation marks each collection when the truck reaches it."
        action={route.status === "active"
          ? <button className="button button--outline button--pause" onClick={() => void pause()} disabled={Boolean(busy)}><Pause size={15} /> Pause route</button>
          : route.status === "planned" || route.status === "paused"
            ? <button className="button button--primary" onClick={() => void startOrResume()} disabled={Boolean(busy)}>{busy === "start" ? <RefreshCw className="spin" size={15} /> : <Play size={15} />}{route.status === "paused" ? "Resume simulation" : "Start simulation"}</button>
            : <span className="status-pill status-pill--collected"><CheckCircle2 size={14} /> Route completed</span>}
      />
      {error && <InlineAlert message={error} onClose={() => setError("")} />}

      <div className="driver-summary">
        <div className="driver-summary-main">
          <div className="driver-route-heading"><div className="truck-heading-icon"><Truck size={21} /></div><div><span className="panel-eyebrow">{route.vehicleName}</span><strong>{route.stops.length} collection stops</strong></div><StatusPill status={route.status === "active" ? "En Route" : route.status === "completed" ? "Collected" : route.status === "paused" ? "Paused" : "Assigned"} /></div>
          <div className="driver-progress"><div className="progress-track"><span style={{ width: `${progress}%` }} /></div><span>{completed} of {route.stops.length} completed</span></div>
          <div className="driver-stat-row"><span><RouteIcon size={15} /> {route.distanceKm.toFixed(1)} km planned</span><span><Clock3 size={15} /> ~{Math.round(route.durationMinutes)} min</span><span><MapPin size={15} /> {nextStop ? `Next: ${nextStop.name}` : "All stops complete"}</span></div>
        </div>
        <div className="speed-control"><span>SIM SPEED</span><div>{[1, 2, 5].map((speed) => <button key={speed} className={route.speedMultiplier === speed ? "selected" : ""} onClick={() => void changeSpeed(speed)} disabled={route.status !== "active" && route.status !== "paused"}>{speed}x</button>)}</div></div>
      </div>

      <div className="dashboard-grid dashboard-grid--driver">
        <section className="panel map-panel">
          <PanelHeading eyebrow="LIVE SIMULATION" title="Truck route" badge={route.status.toUpperCase()} />
          <div className="map-frame map-frame--driver">
            <WasteMap routes={[route]} truckPosition={truckPosition ?? route.currentPosition} />
          </div>
          <div className="map-legend"><LegendDot color="blue" label="Truck position" /><LegendDot color="green" label="Completed stop" /><LegendDot color="amber" label="Next collection" /><span className="map-source">Simulated vehicle movement</span></div>
        </section>
        <section className="panel manifest-panel">
          <PanelHeading eyebrow="ORDERED MANIFEST" title="Stops for this shift" trailing={<span className="small-count">{completed}/{route.stops.length}</span>} />
          {route.stops.map((stop) => (
            <article className={`manifest-stop${stop.status === "Collected" ? " manifest-stop--done" : stop.status === "En Route" ? " manifest-stop--current" : ""}`} key={stop.id}>
              <div className={`stop-number${stop.status === "Collected" ? " stop-number--done" : stop.status === "En Route" ? " stop-number--current" : ""}`}>
                {stop.status === "Collected" ? <Check size={14} /> : String(stop.sequenceNumber).padStart(2, "0")}
              </div>
              <div className="manifest-stop-copy">
                <div className="manifest-stop-title"><strong>{stop.name}</strong><span>{stop.eta}</span></div>
                <span>{stop.wasteType} · {stop.wasteKg.toFixed(1)} kg{stop.address ? ` · ${stop.address}` : ""}</span>
                {stop.description && <small>{stop.description}</small>}
                {stop.status === "En Route" && <div className="stop-actions"><span className="now-label"><span /> CURRENT STOP</span><button className="text-button" onClick={() => void manuallyComplete(stop.id)} disabled={Boolean(busy)}>{busy === stop.id ? "Updating..." : "Mark collected"} <Check size={13} /></button></div>}
              </div>
            </article>
          ))}
          {route.stops.length === 0 && <EmptyState icon={<MapPin size={20} />} title="No stops in this route" text="Ask dispatch to create a route with available collection demand." />}
          <div className="driver-notes"><div className="notes-icon"><Bot size={16} /></div><div><div className="notes-heading">Route handling notes <SourceTag source={route.aiNotesSource} /></div><p>{route.aiRouteNotes || "Follow the municipal standard operating procedure for each waste type."}</p></div></div>
        </section>
      </div>
      <div className="page-footnote"><Activity size={13} /> Stop status syncs to dispatch and citizen tracking as the simulation advances.</div>
    </div>
  );
}

function PageHeading({ kicker, title, description, action }: { kicker: string; title: string; description: string; action?: ReactNode }) {
  return (
    <div className="page-heading">
      <div><div className="page-kicker">{kicker}</div><h1>{title}</h1><p>{description}</p></div>
      {action && <div className="page-heading-action">{action}</div>}
    </div>
  );
}

function PanelHeading({ eyebrow, title, badge, trailing }: { eyebrow: string; title: string; badge?: string; trailing?: ReactNode }) {
  return <div className="panel-heading"><div><div className="panel-eyebrow">{eyebrow}</div><h2>{title}</h2></div>{badge ? <span className="panel-badge">{badge}</span> : trailing}</div>;
}

function MetricCard({ label, value, note, icon, tone }: { label: string; value: string | number; note: string; icon: ReactNode; tone: string }) {
  return <article className="metric-card"><div className={`metric-icon metric-icon--${tone}`}>{icon}</div><span className="metric-label">{label}</span><strong className="metric-value">{value}</strong><span className="metric-note">{note}</span></article>;
}

function ReportRow({
  report,
  showCitizen = false,
  vehicles = [],
  routes = [],
  busy = false,
  disabled = false,
  onAssign,
}: {
  report: Report;
  showCitizen?: boolean;
  vehicles?: Vehicle[];
  routes?: FleetRoute[];
  busy?: boolean;
  disabled?: boolean;
  onAssign?: (reportId: string, vehicleId: string) => void;
}) {
  const [selectedVehicleId, setSelectedVehicleId] = useState("");
  const eligibleVehicles = vehicles.filter((vehicle) => {
    const plannedRoute = routes.find((route) => route.vehicleId === vehicle.id && route.status === "planned");
    return vehicle.available
      && vehicle.driverId
      && vehicle.capacityKg - (plannedRoute?.loadUsedKg ?? 0) >= report.estimatedWasteKg;
  });
  return (
    <article className="report-row">
      <div className={`report-type-icon report-type-icon--${report.wasteType.toLowerCase()}`}>{report.wasteType === "Organic" ? <Leaf size={16} /> : report.wasteType === "Recyclable" ? <Recycle size={16} /> : report.wasteType === "Hazardous" ? <AlertTriangle size={16} /> : <MapPin size={16} />}</div>
      <div className="report-row-copy">
        <div><strong>{report.address || report.description.slice(0, 46)}</strong><StatusPill status={report.status} /></div>
        <span>{report.wasteType} · {report.urgency} priority · {report.estimatedWasteKg} kg{showCitizen ? ` · ${report.citizenName}` : ""}</span>
        {showCitizen && <small className="report-description">{report.description}</small>}
        {report.status === "Pending" && onAssign && (
          <div className="report-assignment">
            <select
              aria-label={`Select driver for report ${report.id}`}
              value={selectedVehicleId}
              onChange={(event) => setSelectedVehicleId(event.target.value)}
              disabled={disabled || eligibleVehicles.length === 0}
            >
              <option value="">{eligibleVehicles.length ? "Select an available truck" : "No available truck with capacity"}</option>
              {eligibleVehicles.map((vehicle) => (
                <option key={vehicle.id} value={vehicle.id}>{vehicle.name} · {vehicle.driverName} · {vehicle.capacityKg} kg</option>
              ))}
            </select>
            <button
              className="button button--primary button--compact"
              onClick={() => onAssign(report.id, selectedVehicleId)}
              disabled={disabled || !selectedVehicleId}
            >
              {busy ? <RefreshCw className="spin" size={14} /> : <Send size={14} />}
              {busy ? "Sending..." : "Assign to driver"}
            </button>
          </div>
        )}
      </div>
      <span className="report-row-time">{timeAgo(report.createdAt)}</span>
    </article>
  );
}

function CitizenReportCard({ report }: { report: Report }) {
  return (
    <article className="citizen-report-card">
      <div className="citizen-report-top"><StatusPill status={report.status} /><span>{new Date(report.createdAt).toLocaleDateString(undefined, { month: "short", day: "numeric" })}</span></div>
      <strong>{report.address || report.description.slice(0, 55)}</strong>
      <p>{report.description}</p>
      <div className="citizen-report-meta"><span>{report.wasteType} · {report.estimatedWasteKg} kg</span>{report.eta && <span><Clock3 size={12} /> ETA {formatEta(report.eta)}</span>}</div>
      {report.photoUrl && <SecurePhoto photoUrl={report.photoUrl} />}
      {report.triageWarning && <small className="triage-warning">{report.triageWarning}</small>}
      <div className="status-timeline">
        {(["Pending", "Assigned", "En Route", "Collected"] as const).map((step, index) => {
          const statuses = ["Pending", "Assigned", "En Route", "Collected"];
          const currentIndex = statuses.indexOf(report.status);
          return <span className={index <= currentIndex ? "done" : ""} key={step}><i />{step}</span>;
        })}
      </div>
    </article>
  );
}

function SecurePhoto({ photoUrl }: { photoUrl: string }) {
  const [url, setUrl] = useState("");
  const [failed, setFailed] = useState(false);
  useEffect(() => {
    let disposed = false;
    let objectUrl = "";
    api.getProtectedPhoto(photoUrl)
      .then((loaded) => {
        objectUrl = loaded;
        if (disposed) URL.revokeObjectURL(loaded);
        else setUrl(loaded);
      })
      .catch(() => setFailed(true));
    return () => {
      disposed = true;
      if (objectUrl) URL.revokeObjectURL(objectUrl);
    };
  }, [photoUrl]);
  if (failed) return <small className="photo-unavailable"><FileImage size={13} /> Photo unavailable</small>;
  if (!url) return <small className="photo-unavailable"><RefreshCw size={13} className="spin" /> Loading photo</small>;
  return <img className="report-photo" src={url} alt="Attached waste report" />;
}

function TriageCard({ triage }: { triage: Triage }) {
  return <div className="triage-card"><div className="triage-card-title"><Bot size={16} /><strong>Report triage preview</strong><SourceTag source={triage.source} /></div><div className="triage-tags"><span>{triage.wasteType}</span><span>{triage.urgency} urgency</span><span>Priority {triage.priorityScore}/100</span><span>~{triage.estimatedWasteKg} kg</span></div><p>{triage.handlingInstructions}</p>{triage.warning && <small>{triage.warning}</small>}</div>;
}

function StatusPill({ status }: { status: string }) {
  const normalized = status.toLowerCase().replaceAll(" ", "-");
  return <span className={`status-pill status-pill--${normalized}`}><i />{status}</span>;
}

function SourceTag({ source }: { source: string }) {
  const cloudSource = source.toLowerCase().includes("groq") || source.toLowerCase().includes("cloud");
  return <span className={`source-tag${cloudSource ? " source-tag--cloud" : ""}`}>{cloudSource ? <Cloud size={11} /> : <Cpu size={11} />}{source.replaceAll("_", " ")}</span>;
}

function LegendDot({ color, label }: { color: "green" | "amber" | "blue"; label: string }) {
  return <span className="legend-dot"><i className={`legend-dot__${color}`} />{label}</span>;
}

function EmptyState({ icon, title, text }: { icon: ReactNode; title: string; text: string }) {
  return <div className="empty-state"><div>{icon}</div><strong>{title}</strong><p>{text}</p></div>;
}

function DashboardError({ error, onRetry }: { error: string; onRetry: () => void }) {
  return <div className="dashboard-content"><div className="error-state"><AlertTriangle size={24} /><h2>Could not load this workspace</h2><p>{error}</p><button className="button button--outline" onClick={onRetry}><RefreshCw size={15} /> Try again</button></div></div>;
}

function InlineAlert({ message, onClose }: { message: string; onClose: () => void }) {
  return <div className="inline-error"><AlertTriangle size={16} /><span>{message}</span><button onClick={onClose} aria-label="Dismiss error"><X size={15} /></button></div>;
}

function LoadingScreen({ label }: { label: string }) {
  return <div className="loading-screen"><div className="loading-mark"><Recycle size={23} /></div><RefreshCw className="spin" size={17} /><span>{label}</span></div>;
}

function roleLabel(role: Role) {
  return role === "admin" ? "Administrator" : role === "driver" ? "Driver" : "Citizen";
}

function errorMessage(error: unknown) {
  return error instanceof Error ? error.message : "Something went wrong. Please try again.";
}

function timeAgo(value: string) {
  const elapsed = Math.max(0, Date.now() - new Date(value).getTime());
  const minutes = Math.floor(elapsed / 60000);
  if (minutes < 1) return "Just now";
  if (minutes < 60) return `${minutes}m ago`;
  const hours = Math.floor(minutes / 60);
  return hours < 24 ? `${hours}h ago` : `${Math.floor(hours / 24)}d ago`;
}

function formatEta(value: string) {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return new Intl.DateTimeFormat(undefined, { hour: "2-digit", minute: "2-digit" }).format(date);
}

function haversineKm(a: { latitude: number; longitude: number }, b: { latitude: number; longitude: number }) {
  const rad = (degrees: number) => degrees * Math.PI / 180;
  const dLat = rad(b.latitude - a.latitude);
  const dLon = rad(b.longitude - a.longitude);
  const h = Math.sin(dLat / 2) ** 2 + Math.cos(rad(a.latitude)) * Math.cos(rad(b.latitude)) * Math.sin(dLon / 2) ** 2;
  return 6371 * 2 * Math.asin(Math.sqrt(h));
}

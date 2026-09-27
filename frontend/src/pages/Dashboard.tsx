import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import AnomalyDrawer from "../components/AnomalyDrawer";
import { MachineDrawer } from "../components/MachineOps";
import AnalyticsView from "../views/AnalyticsView";
import AnomaliesView from "../views/AnomaliesView";
import DataView from "../views/DataView";
import MachinesView from "../views/MachinesView";
import OverviewView from "../views/OverviewView";
import ReportsView from "../views/ReportsView";
import { VIEWS, criticalCount, fmtPeriod, sourceLabel, type ViewId } from "../views/viewData";
import type {
  AnalyticsReport,
  Anomaly,
  DemoParams,
  GeneratedReport,
  MachineKPIs,
  PlantObservation,
  ProviderStatus,
  ReportType,
  UploadProfile,
  UploadResult,
} from "../services/api";
import {
  DEMO_PARAMS,
  exportReportHtml,
  fetchAnalytics,
  fetchObservations,
  fetchReportStatus,
  fetchUploadProfiles,
  generateReport,
  generateReportFromAnalytics,
  uploadPlantCsv,
} from "../services/api";

export default function Dashboard() {
  const [view, setView] = useState<ViewId>("overview");
  const [analytics, setAnalytics] = useState<AnalyticsReport | null>(null);
  const [observations, setObservations] = useState<PlantObservation[]>([]);
  const [report, setReport] = useState<GeneratedReport | null>(null);
  const [status, setStatus] = useState<ProviderStatus | null>(null);
  const [profiles, setProfiles] = useState<UploadProfile[]>([]);
  const [params, setParams] = useState<DemoParams>(DEMO_PARAMS);
  const [reportType, setReportType] = useState<ReportType>("daily");
  const [dataSource, setDataSource] = useState<"simulator" | "upload" | null>(null);
  const [uploadName, setUploadName] = useState<string | null>(null);
  const [lastUpload, setLastUpload] = useState<DataViewProps["lastResult"]>(null);

  const [loading, setLoading] = useState(true);
  const [loadError, setLoadError] = useState("");
  const [reportBusy, setReportBusy] = useState(false);
  const [reportError, setReportError] = useState("");
  const [history, setHistory] = useState<GeneratedReport[]>([]);
  const [genSeq, setGenSeq] = useState(0);
  const [uploadBusy, setUploadBusy] = useState(false);
  const [uploadError, setUploadError] = useState("");

  const [openAnomaly, setOpenAnomaly] = useState<Anomaly | null>(null);
  const [openMachine, setOpenMachine] = useState<MachineKPIs | null>(null);
  const [updatedAt, setUpdatedAt] = useState<Date | null>(null);

  const abortRef = useRef<AbortController | null>(null);

  const load = useCallback(async (p: DemoParams) => {
    abortRef.current?.abort();
    const ctrl = new AbortController();
    abortRef.current = ctrl;
    const { signal } = ctrl;
    setLoading(true);
    setLoadError("");
    try {
      const [a, o] = await Promise.all([fetchAnalytics(p, signal), fetchObservations(p, signal)]);
      if (signal.aborted) return;
      setAnalytics(a);
      setObservations(o);
      setUpdatedAt(new Date());
    } catch (e) {
      if (signal.aborted || (e instanceof DOMException && e.name === "AbortError")) return;
      setLoadError(e instanceof Error ? e.message : "Could not reach the analytics service.");
      setLoading(false);
      return;
    }
    // Provider status is a cheap, non-LLM call and is independent of the
    // analytics. A missing key or rate limit must never take the dashboard
    // down, so failures here are swallowed.
    try {
      const s = await fetchReportStatus(signal);
      if (!signal.aborted) setStatus(s);
    } catch {
      if (!signal.aborted) setStatus(null);
    } finally {
      if (!signal.aborted) setLoading(false);
    }
  }, []);

  useEffect(() => {
    // oxlint-disable-next-line react/set-state-in-effect
    setDataSource("simulator");
    void load(DEMO_PARAMS);
    fetchUploadProfiles().then(setProfiles).catch(() => setProfiles([]));
    return () => abortRef.current?.abort();
  }, [load]);

  const applyParams = (p: DemoParams) => {
    setParams(p);
    setDataSource("simulator");
    setUploadName(null);
    void load(p);
  };

  const doUpload = async (file: File, profile: string) => {
    setUploadBusy(true);
    setUploadError("");
    try {
      const r: UploadResult = await uploadPlantCsv(file, profile);
      setAnalytics(r.analytics);
      setObservations(r.observations);
      setDataSource("upload");
      setUploadName(r.filename);
      setUpdatedAt(new Date());
      setLastUpload({
        filename: r.filename,
        profile: r.profile,
        csv_rows: r.csv_rows,
        observation_count: r.observation_count,
        derived: r.derived_fields,
      });
      setView("overview");
    } catch (e) {
      setUploadError(e instanceof Error ? e.message : "Upload failed.");
    } finally {
      setUploadBusy(false);
    }
  };

  const doGenerate = async () => {
    setReportBusy(true);
    setReportError("");
    setGenSeq((n) => n + 1);
    try {
      const r =
        dataSource === "upload" && analytics
          ? await generateReportFromAnalytics(analytics, reportType)
          : await generateReport(reportType, params);
      setReport(r);
      setHistory((h) => [r, ...h].slice(0, 12));
    } catch (e) {
      setReportError(e instanceof Error ? e.message : "Report generation failed.");
    } finally {
      setReportBusy(false);
    }
  };

  const download = (text: string, filename: string, type: string) => {
    const blob = new Blob([text], { type });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = filename;
    document.body.appendChild(a);
    a.click();
    a.remove();
    URL.revokeObjectURL(url);
  };

  const stamp = report ? new Date(report.generated_at) : new Date();

  const plantState = useMemo(() => {
    if (!analytics) return { label: "Unknown", cls: "pill-unknown", title: "No analytics loaded" };
    const crit = criticalCount(analytics);
    if (crit > 0)
      return {
        label: "Attention",
        cls: "pill-critical",
        title: `${crit} critical anomalies in this period`,
      };
    if (analytics.plant.fault_count > 0)
      return { label: "Faults", cls: "pill-high", title: "Machine faults recorded" };
    if (analytics.anomalies.length > 0)
      return { label: "Watch", cls: "pill-medium", title: "Anomalies below critical" };
    return { label: "Nominal", cls: "pill-ok", title: "No anomalies detected" };
  }, [analytics]);

  const period = fmtPeriod(analytics);
  const current = VIEWS.find((v) => v.id === view)!;

  return (
    <div className="shell">
      <aside className="sidebar">
        <div className="brand">
          <div className="brand-name">
            Plant
            <br />
            Intelligence
          </div>
          <div className="brand-sub">P041 · Operations console</div>
        </div>

        <div className="sysline">
          <span
            className="mark"
            style={{ color: loadError ? "var(--critical)" : "var(--ok)" }}
            aria-hidden="true"
          />
          <span className="sysline-text">{loadError ? "Service error" : "System online"}</span>
        </div>

        <nav className="nav" aria-label="Console sections">
          {VIEWS.map((v) => (
            <button
              key={v.id}
              className="nav-item"
              aria-current={view === v.id ? "page" : undefined}
              /* The rail collapses to ordinals-only below 1024px, so the full
                 label must stay in the accessible name and the tooltip. */
              aria-label={v.label}
              title={v.label}
              onClick={() => setView(v.id)}
            >
              <span className="nav-num" aria-hidden="true">{v.num}</span>
              <span className="nav-label">{v.label}</span>
            </button>
          ))}
        </nav>

        <div className="sidebar-foot">
          <div className="readout" style={{ marginBottom: "0.5rem" }}>
            <span className="readout-label">Last refresh</span>
            <span className="readout-value">
              {updatedAt
                ? updatedAt.toLocaleTimeString("en-GB", {
                    hour: "2-digit",
                    minute: "2-digit",
                    second: "2-digit",
                  })
                : "—"}
            </span>
          </div>
          <div className="readout" style={{ marginBottom: "0.5rem" }}>
            <span className="readout-label">Observations</span>
            <span className="readout-value">
              {analytics ? analytics.plant.observation_count.toLocaleString() : "—"}
            </span>
          </div>
          <div className="readout">
            <span className="readout-label">Provider</span>
            <span className="readout-value">
              {status?.mode === "live" ? (status.model ?? status.provider) : (status?.mode ?? "—")}
            </span>
          </div>
          <div className="sidebar-foot-brand">
            P041
            <br />
            Hackathon MVP
          </div>
        </div>
      </aside>

      <header className="topbar">
        <div className="topbar-id">
          <span className="topbar-title">Plant Intelligence</span>
          <span className="topbar-sub">Industrial operations console</span>
          <span className="readout topbar-period">
            <span className="readout-label">Period</span>
            <span className="readout-value">
              {period.date} {period.span}
            </span>
          </span>
        </div>

        <div className="topbar-center">
          <div className="readout">
            <span className="readout-label">Data mode</span>
            <span className="readout-value">{sourceLabel(dataSource, params, uploadName)}</span>
          </div>
        </div>

        <div className="topbar-actions">
          <span className={`pill ${plantState.cls}`} title={plantState.title}>
            {plantState.label}
          </span>
          {status?.mode === "live" && (
            <span className="pill pill-ok" title={`Provider ${status.provider}`}>
              Live LLM
            </span>
          )}
          {status?.mode === "unconfigured" && <span className="pill pill-high">LLM off</span>}
          <button
            className="btn"
            onClick={() => {
              setDataSource("simulator");
              setUploadName(null);
              void load(params);
            }}
            disabled={loading}
          >
            {loading ? "Refreshing…" : "Refresh"}
          </button>
          <button
            className="btn btn-primary"
            onClick={() => {
              // This button says "generate", so it generates. Navigation to the
              // report view happens alongside, not instead.
              setView("reports");
              void doGenerate();
            }}
            disabled={reportBusy}
          >
            {reportBusy ? "Generating…" : "Generate report"}
          </button>
        </div>
      </header>

      <main className="workspace">
        {loadError ? (
          <div className="view">
            <div className="state state-error">
              <div className="state-title">Analytics service unreachable</div>
              <p>{loadError}</p>
              <p>
                The console reads from the FastAPI backend. Check that it is running and that
                VITE_API_BASE_URL points at it, then retry.
              </p>
              <button className="btn btn-primary" onClick={() => void load(params)}>
                Retry
              </button>
            </div>
          </div>
        ) : !analytics ? (
          <div className="view">
            <div className="state">
              <div className="state-title">Loading plant data</div>
              <p>Requesting the analytics report and raw observations.</p>
            </div>
            <div className="kpi-strip" aria-hidden="true">
              {[0, 1, 2, 3, 4].map((i) => (
                <div className="skel" key={i} />
              ))}
            </div>
          </div>
        ) : (
          <div className="view" key={view}>
            {loading && (
              <div className="busy-strip" role="status">
                <span className="busy-dot" /> Refreshing — showing the previous dataset until the
                new one arrives
              </div>
            )}

            {view === "overview" && (
              <OverviewView
                analytics={analytics}
                observations={observations}
                onOpenAnomaly={(a) => setOpenAnomaly(a)}
                onOpenMachine={setOpenMachine}
                onGoAnalytics={() => setView("analytics")}
              />
            )}
            {view === "analytics" && <AnalyticsView analytics={analytics} observations={observations} />}
            {view === "machines" && (
              <MachinesView
                analytics={analytics}
                observations={observations}
                onOpenMachine={setOpenMachine}
                onOpenAnomaly={(a) => setOpenAnomaly(a)}
              />
            )}
            {view === "anomalies" && (
              <AnomaliesView analytics={analytics} onOpen={(a) => setOpenAnomaly(a)} />
            )}
            {view === "reports" && (
              <ReportsView
                report={report}
                statusMode={status?.mode ?? null}
                statusModel={status?.model ?? null}
                reportType={reportType}
                busy={reportBusy}
                error={reportError}
                history={history}
                summary={{
                  total_production: analytics.plant.total_production,
                  average_efficiency: analytics.plant.average_efficiency,
                  total_energy_kwh: analytics.plant.total_energy_kwh,
                  total_downtime_minutes: analytics.plant.total_downtime_minutes,
                  anomaly_count: analytics.anomalies.length,
                  machine_count: analytics.plant.machine_count,
                }}
                onTypeChange={(t) => {
                  setReportType(t);
                  if (dataSource !== "upload") void load(params);
                }}
                onGenerate={() => void doGenerate()}
                onSelectHistory={setReport}
                genSeq={genSeq}
                onDownload={() =>
                  report && download(report.content, `plant-report-${stamp.toISOString().slice(0, 10)}.md`, "text/markdown")
                }
                onDownloadHtml={() => {
                  if (!report) return;
                  exportReportHtml(report)
                    .then((html) =>
                      download(html, `plant-report-${stamp.toISOString().slice(0, 10)}.html`, "text/html"),
                    )
                    .catch(() => setReportError("HTML export failed."));
                }}
              />
            )}
            {view === "data" && (
              <DataView
                params={params}
                onParams={applyParams}
                profiles={profiles}
                uploadBusy={uploadBusy}
                uploadError={uploadError}
                lastResult={lastUpload}
                onUpload={(f, p) => void doUpload(f, p)}
              />
            )}

            <p className="panel-note" style={{ marginTop: "0.4rem" }}>
              {current.title} · last updated{" "}
              {updatedAt ? updatedAt.toLocaleTimeString("en-GB", { hour: "2-digit", minute: "2-digit", second: "2-digit" }) : "—"}
            </p>
          </div>
        )}
      </main>

      {openAnomaly && (
        <AnomalyDrawer anomaly={openAnomaly} onClose={() => setOpenAnomaly(null)} />
      )}
      {openMachine && (
        <MachineDrawer
          machine={openMachine}
          anomalies={analytics?.anomalies ?? []}
          observations={observations}
          onClose={() => setOpenMachine(null)}
        />
      )}
    </div>
  );
}

type DataViewProps = {
  lastResult: {
    filename: string;
    profile: string;
    csv_rows: number;
    observation_count: number;
    derived: string[];
  } | null;
};

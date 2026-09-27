import { useEffect, useState } from "react";
import ReportDoc from "../components/ReportDoc";
import type { GeneratedReport, ReportType } from "../services/api";

interface Props {
  report: GeneratedReport | null;
  statusMode: string | null;
  statusModel: string | null;
  reportType: ReportType;
  busy: boolean;
  error: string;
  history: GeneratedReport[];
  /** Live analytics figures, shown whether or not a report exists yet. */
  summary: {
    total_production: number;
    average_efficiency: number;
    total_energy_kwh: number;
    total_downtime_minutes: number;
    anomaly_count: number;
    machine_count: number;
  };
  onTypeChange: (t: ReportType) => void;
  onGenerate: () => void;
  onSelectHistory: (r: GeneratedReport) => void;
  onDownload: () => void;
  onDownloadHtml: () => void;
  /** Increments per generation so the elapsed timer restarts. */
  genSeq: number;
}

const TYPES: ReportType[] = ["daily", "weekly", "monthly"];

/** Elapsed seconds for a request that is genuinely in flight. */
function Elapsed({ seq, active }: { seq: number; active: boolean }) {
  const [secs, setSecs] = useState(0);
  useEffect(() => {
    if (!active) return;
    const t0 = Date.now();
    const id = setInterval(() => setSecs(Math.floor((Date.now() - t0) / 1000)), 1000);
    return () => clearInterval(id);
    // seq restarts the clock for each new generation.
  }, [active, seq]);
  if (!active) return null;
  return <>{secs}s</>;
}

function trustOf(report: GeneratedReport | null): { cls: string; text: string } {
  if (!report) return { cls: "trust-pending", text: "Not generated" };
  // The backend check reports whether every required figure was reproduced
  // verbatim. It is a completeness signal, not a claim of correctness.
  return report.numbers_verified
    ? { cls: "trust-ok", text: "Analytics grounded · verified" }
    : { cls: "trust-warn", text: "Validation warning" };
}

export default function ReportsView({
  report,
  statusMode,
  statusModel,
  reportType,
  busy,
  error,
  history,
  summary,
  onTypeChange,
  onGenerate,
  onSelectHistory,
  onDownload,
  onDownloadHtml,
  genSeq,
}: Props) {
  const trust = trustOf(report);

  const providerLabel =
    statusMode === "live" ? "Live LLM" : statusMode === "unconfigured" ? "Not configured" : "Unknown";

  return (
    <>
      <header className="view-head">
        <div>
          <h1 className="view-title">Report workstation</h1>
          <p className="view-sub">
            Narrative is written by the model from the analytics above; no figure is computed by the
            model
          </p>
        </div>
        <div className="view-facts">
          <div className="readout">
            <span className="readout-label">Provider</span>
            <span className="readout-value">
              {report?.provider ?? statusMode ?? "—"}
            </span>
          </div>
          <div className="readout">
            <span className="readout-label">Mode</span>
            <span className="readout-value">{providerLabel}</span>
          </div>
          <div className="readout">
            <span className="readout-label">Model</span>
            <span className="readout-value">{report?.model ?? statusModel ?? "—"}</span>
          </div>
        </div>
      </header>

      <section className="grid-12">
        {/* left: cadence + history */}
        <div className="col-3">
          <div className="panel">
            <div className="panel-head">
              <h3 className="panel-title">Cadence</h3>
            </div>
            <div style={{ display: "flex", flexDirection: "column", gap: "0.35rem" }}>
              {TYPES.map((t) => (
                <button
                  key={t}
                  className="chip"
                  aria-pressed={reportType === t}
                  onClick={() => onTypeChange(t)}
                  style={{ textAlign: "left" }}
                >
                  {t}
                </button>
              ))}
            </div>
            <button
              className="btn btn-primary"
              style={{ width: "100%", justifyContent: "center", marginTop: "0.7rem" }}
              onClick={onGenerate}
              disabled={busy}
            >
              {busy ? "Generating…" : "Generate report"}
            </button>
            {busy && (
              <div className="busy-strip" style={{ marginTop: "0.5rem" }} role="status">
                <span className="busy-dot" />
                Request in flight · <Elapsed seq={genSeq} active={busy} />
              </div>
            )}
            {statusMode === "unconfigured" && (
              <p className="panel-note" style={{ marginTop: "0.5rem" }}>
                Set LLM_API_KEY in backend/.env to enable generation.
              </p>
            )}
          </div>

          <div className="panel" style={{ marginTop: "1rem" }}>
            <div className="panel-head">
              <h3 className="panel-title">This session</h3>
              <span className="panel-note">{history.length}</span>
            </div>
            {history.length === 0 ? (
              <p className="panel-note">Reports generated in this session appear here.</p>
            ) : (
              <div className="events">
                {history.map((r, i) => (
                  <button
                    key={`${r.generated_at}-${i}`}
                    className="event"
                    style={{ gridTemplateColumns: "1fr auto", borderLeftColor: "var(--line-strong)" }}
                    onClick={() => onSelectHistory(r)}
                  >
                    <span className="event-metric">{r.report_type}</span>
                    <span className="event-time">
                      {new Date(r.generated_at).toLocaleTimeString("en-GB", { hour: "2-digit", minute: "2-digit" })}
                    </span>
                    <span className="event-reason">
                      {r.numbers_verified ? "verified" : "validation warning"} · {r.model}
                    </span>
                  </button>
                ))}
              </div>
            )}
          </div>
        </div>

        {/* centre: the report */}
        <div className="col-6">
          <div className="panel">
            <div className="panel-head">
              <h3 className="panel-title">AI plant report</h3>
              <span className={`trust ${trust.cls}`}>{trust.text}</span>
            </div>

            {error && (
              <div className="callout callout-error" role="alert" style={{ marginBottom: "0.8rem" }}>
                {error}
              </div>
            )}

            {!report && !busy && !error && (
              <div className="state">
                <div className="state-title">No report generated yet</div>
                <p>
                  The narrative is written by {statusMode === "live" ? "the configured model" : "a provider"} from
                  the analytics on the other screens. It never computes a figure itself: the
                  figures below are the ones it must reproduce, and each is checked after
                  generation.
                </p>
                <div className="metrics-2">
                  <div className="metric-cell">
                    <div className="metric-label">Production</div>
                    <div className="metric-value">
                      {summary.total_production.toLocaleString()}
                      <span className="unit">units</span>
                    </div>
                  </div>
                  <div className="metric-cell">
                    <div className="metric-label">Efficiency</div>
                    <div className="metric-value">{summary.average_efficiency.toFixed(2)}%</div>
                  </div>
                  <div className="metric-cell">
                    <div className="metric-label">Energy</div>
                    <div className="metric-value">
                      {summary.total_energy_kwh.toLocaleString()}
                      <span className="unit">kWh</span>
                    </div>
                  </div>
                  <div className="metric-cell">
                    <div className="metric-label">Downtime</div>
                    <div className="metric-value">
                      {summary.total_downtime_minutes.toLocaleString()}
                      <span className="unit">min</span>
                    </div>
                  </div>
                  <div className="metric-cell">
                    <div className="metric-label">Anomalies</div>
                    <div className="metric-value">{summary.anomaly_count}</div>
                  </div>
                  <div className="metric-cell">
                    <div className="metric-label">Machines</div>
                    <div className="metric-value">{summary.machine_count}</div>
                  </div>
                </div>
                <p className="panel-note" style={{ margin: "0.8rem 0 0" }}>
                  Choose a cadence and select Generate report. A provider request is only made when
                  you ask for one.
                </p>
              </div>
            )}
            {busy && !report && <p className="panel-note">Waiting for the model to respond…</p>}
            {report && <ReportDoc content={report.content} />}
          </div>
        </div>

        {/* right: metadata + export */}
        <div className="col-3">
          <div className="panel">
            <div className="panel-head">
              <h3 className="panel-title">Provenance</h3>
            </div>
            {report ? (
              <dl className="dl">
                <dt>Type</dt>
                <dd className="mono">{report.report_type}</dd>
                <dt>Period</dt>
                <dd className="mono" style={{ fontSize: "0.76rem" }}>{report.reporting_period}</dd>
                <dt>Generated</dt>
                <dd className="mono" style={{ fontSize: "0.76rem" }}>
                  {new Date(report.generated_at).toLocaleString()}
                </dd>
                <dt>Provider</dt>
                <dd className="mono">{report.provider}</dd>
                <dt>Model</dt>
                <dd className="mono" style={{ fontSize: "0.76rem" }}>{report.model}</dd>
                <dt>Grounding</dt>
                <dd>
                  <span className={`trust ${report.numbers_verified ? "trust-ok" : "trust-warn"}`}>
                    {report.numbers_verified ? "verified" : "warning"}
                  </span>
                </dd>
              </dl>
            ) : (
              <p className="panel-note">Available once a report is generated.</p>
            )}
            <p className="panel-note" style={{ marginTop: "0.7rem" }}>
              Grounding compares every required figure against the generated text. A warning means
              a figure was not reproduced verbatim — not that the model altered the analytics.
            </p>
          </div>

          <div className="panel" style={{ marginTop: "1rem" }}>
            <div className="panel-head">
              <h3 className="panel-title">Source figures</h3>
            </div>
            <dl className="dl">
              {Object.entries(
                report ? report.analytics_summary : summary,
              ).map(([k, v]) => (
                <div key={k} style={{ display: "contents" }}>
                  <dt>{k.replace(/_/g, " ")}</dt>
                  <dd className="mono">
                    {typeof v === "number" ? v.toLocaleString() : String(v)}
                  </dd>
                </div>
              ))}
            </dl>
          </div>

          <div className="panel" style={{ marginTop: "1rem" }}>
            <div className="panel-head">
              <h3 className="panel-title">Export</h3>
            </div>
            <div style={{ display: "flex", flexDirection: "column", gap: "0.35rem" }}>
              <button className="btn" onClick={onDownload} disabled={!report}>
                Download markdown
              </button>
              <button className="btn" onClick={onDownloadHtml} disabled={!report}>
                Download HTML
              </button>
            </div>
          </div>
        </div>
      </section>
    </>
  );
}

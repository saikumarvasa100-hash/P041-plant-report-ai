import { useMemo, useState } from "react";
import { SeverityBar } from "../components/HealthPanel";
import { METRIC_UNIT, fmtStamp, metricLabel, rankAnomalies, severityCounts } from "../lib/format";
import type { AnalyticsReport, Anomaly } from "../services/api";

interface Props {
  analytics: AnalyticsReport;
  onOpen: (a: Anomaly, trigger: HTMLElement) => void;
}

type Filter = "all" | Anomaly["severity"];
const FILTERS: Filter[] = ["all", "critical", "high", "medium", "low"];

const PAGE = 40;

/** Dense investigation table: totals, distribution, filter, evidence rows. */
export default function AnomaliesView({ analytics, onOpen }: Props) {
  const [filter, setFilter] = useState<Filter>("all");
  const counts = severityCounts(analytics.anomalies);
  const ranked = useMemo(() => rankAnomalies(analytics.anomalies), [analytics.anomalies]);
  const filtered = useMemo(
    () => (filter === "all" ? ranked : ranked.filter((a) => a.severity === filter)),
    [ranked, filter],
  );
  const shown = filtered.slice(0, PAGE);
  const machines = useMemo(
    () => [...new Set(analytics.anomalies.map((a) => a.machine_id))].sort(),
    [analytics.anomalies],
  );

  return (
    <>
      <header className="view-head">
        <div>
          <h1 className="view-title">Anomaly investigation</h1>
          <p className="view-sub">
            {analytics.anomalies.length} detections across {machines.length} machines ·{" "}
            {analytics.plant.observation_count.toLocaleString()} observations scanned
          </p>
        </div>
        <div className="view-facts">
          <div className="readout">
            <span className="readout-label">Total</span>
            <span className="readout-value">{analytics.anomalies.length}</span>
          </div>
          {(["critical", "high", "medium", "low"] as const).map((s) => (
            <div className="readout" key={s}>
              <span className="readout-label">{s}</span>
              <span className="readout-value">{counts[s]}</span>
            </div>
          ))}
        </div>
      </header>

      <div className="panel">
        <SeverityBar anomalies={analytics.anomalies} />
        <div style={{ marginTop: "0.5rem" }}>
          <div className="sevlist sevlist-grid">
            {(["critical", "high", "medium", "low"] as const).map((s) => (
              <div key={s} className="sevlist-row">
                <span className={`mark mark-${s}`}>{s}</span>
                <span className="sevlist-n">{counts[s]}</span>
              </div>
            ))}
          </div>
        </div>
      </div>

      <div className="panel">
        <div className="panel-head">
          <h3 className="panel-title">
            Detections {filter !== "all" ? `· ${filter}` : ""} ({filtered.length})
          </h3>
          <div className="filters" role="group" aria-label="Filter anomalies by severity">
            {FILTERS.map((f) => (
              <button
                key={f}
                className="chip"
                aria-pressed={filter === f}
                onClick={() => setFilter(f)}
              >
                {f} · {f === "all" ? analytics.anomalies.length : counts[f]}
              </button>
            ))}
          </div>
        </div>

        {shown.length === 0 ? (
          <p className="panel-note">No anomalies at this severity in the reporting window.</p>
        ) : (
          <div className="table-scroll">
            <table>
              <thead>
                <tr>
                  <th>Severity</th>
                  <th>Machine</th>
                  <th>Metric</th>
                  <th className="num">Value</th>
                  <th className="num">Expected</th>
                  <th>Timestamp</th>
                  <th>Detector</th>
                  <th>Reason</th>
                </tr>
              </thead>
              <tbody>
                {shown.map((a, i) => (
                  <tr
                    key={`${a.machine_id}-${a.timestamp}-${a.metric}-${i}`}
                    onClick={() => onOpen(a, document.activeElement as HTMLElement)}
                    tabIndex={0}
                    role="button"
                    aria-label={`${a.severity} anomaly, ${a.machine_id}, ${metricLabel(a.metric)}`}
                    onKeyDown={(e) => {
                      if (e.key === "Enter" || e.key === " ") {
                        e.preventDefault();
                        onOpen(a, e.currentTarget);
                      }
                    }}
                    style={{ cursor: "pointer" }}
                  >
                    <td>
                      <span className={`mark mark-${a.severity}`}>{a.severity}</span>
                    </td>
                    <td className="mono">{a.machine_id}</td>
                    <td>{metricLabel(a.metric)}</td>
                    <td className="num">
                      {a.value}
                      {METRIC_UNIT[a.metric] ?? ""}
                    </td>
                    <td className="num">
                      {a.expected !== null ? `${a.expected}${METRIC_UNIT[a.metric] ?? ""}` : "—"}
                    </td>
                    <td className="mono" style={{ fontSize: "0.76rem" }}>{fmtStamp(a.timestamp)}</td>
                    <td className="mono" style={{ fontSize: "0.76rem" }}>{a.detector}</td>
                    <td style={{ whiteSpace: "normal", maxWidth: "22rem", color: "var(--ink-2)" }}>
                      {a.reason}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
        {filtered.length > PAGE && (
          <p className="panel-note" style={{ marginTop: "0.6rem" }}>
            Showing the {PAGE} highest-priority of {filtered.length}. Narrow the severity filter to
            see the rest.
          </p>
        )}
      </div>
    </>
  );
}

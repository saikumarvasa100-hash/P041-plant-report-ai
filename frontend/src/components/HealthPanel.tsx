import type { Anomaly } from "../services/api";
import { SEVERITIES, severityCounts } from "../lib/format";

interface Props {
  anomalies: Anomaly[];
}

/** Severity distribution, straight from the backend anomaly list. */
export function SeverityBar({ anomalies }: Props) {
  const counts = severityCounts(anomalies);
  const total = anomalies.length;
  if (total === 0) return null;
  return (
    <div
      className="sevbar"
      role="img"
      aria-label={SEVERITIES.filter((s) => counts[s] > 0)
        .map((s) => `${counts[s]} ${s}`)
        .join(", ")}
    >
      {SEVERITIES.map((s) =>
        counts[s] > 0 ? (
          <div key={s} className={`sevbar-seg ${s}`} style={{ width: `${(counts[s] / total) * 100}%` }} />
        ) : null,
      )}
    </div>
  );
}

export function SeverityList({ anomalies }: Props) {
  const counts = severityCounts(anomalies);
  return (
    <div className="sevlist">
      {SEVERITIES.map((s) => (
        <div key={s} className="sevlist-row">
          <span className={`mark mark-${s}`}>{s}</span>
          <span className="sevlist-n">{counts[s]}</span>
        </div>
      ))}
    </div>
  );
}

/** Executive summary of anomaly load. No health verdict is invented. */
export default function HealthPanel({ anomalies }: Props) {
  const counts = severityCounts(anomalies);
  return (
    <div className="panel">
      <div className="panel-head">
        <h3 className="panel-title">Operational health</h3>
      </div>
      <div className="kpi-label">Total anomalies</div>
      <div className="kpi-value">{anomalies.length}</div>
      <div style={{ margin: "0.7rem 0 0.5rem" }}>
        <SeverityBar anomalies={anomalies} />
      </div>
      <SeverityList anomalies={anomalies} />
      <dl className="dl" style={{ marginTop: "0.7rem" }}>
        <dt>Critical</dt>
        <dd>
          {counts.critical > 0
            ? `${counts.critical} above configured critical thresholds.`
            : "None above critical thresholds."}
        </dd>
      </dl>
    </div>
  );
}

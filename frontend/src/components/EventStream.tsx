import { METRIC_UNIT, fmtTime, metricLabel, rankAnomalies } from "../lib/format";
import type { Anomaly } from "../services/api";

interface Props {
  anomalies: Anomaly[];
  limit?: number;
  onOpen: (a: Anomaly, trigger: HTMLElement) => void;
}

/** Compact clickable event stream. Each row opens the detail drawer. */
export default function EventStream({ anomalies, limit = 7, onOpen }: Props) {
  const rows = rankAnomalies(anomalies).slice(0, limit);
  if (rows.length === 0) {
    return (
      <div className="panel">
        <div className="panel-head">
          <h3 className="panel-title">Critical events</h3>
        </div>
        <p className="panel-note">No anomalies detected in this period.</p>
      </div>
    );
  }
  return (
    <div className="panel">
      <div className="panel-head">
        <h3 className="panel-title">Critical events</h3>
        <span className="panel-note">Highest severity first</span>
      </div>
      <div className="events">
        {rows.map((a, i) => (
          <button
            key={`${a.machine_id}-${a.timestamp}-${a.metric}-${i}`}
            className={`event ${a.severity}`}
            onClick={(e) => onOpen(a, e.currentTarget)}
            aria-label={`${a.severity} anomaly on ${a.machine_id}: ${metricLabel(a.metric)} ${a.value}`}
          >
            <span className={`mark mark-${a.severity}`}>{a.severity}</span>
            <span className="event-metric">
              {a.machine_id} · {metricLabel(a.metric)}{" "}
              <span className="mono">
                {a.value}
                {METRIC_UNIT[a.metric] ?? ""}
              </span>
            </span>
            <span className="event-time">{fmtTime(a.timestamp)}</span>
            <span className="event-reason">{a.reason}</span>
          </button>
        ))}
      </div>
    </div>
  );
}

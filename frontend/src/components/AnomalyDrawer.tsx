import Drawer from "./Drawer";
import type { Anomaly } from "../services/api";
import { METRIC_UNIT, fmtStamp, metricLabel } from "../lib/format";

interface Props {
  anomaly: Anomaly;
  onClose: () => void;
}

/** Anomaly evidence drawer. Backend fields shown verbatim. */
export default function AnomalyDrawer({ anomaly, onClose }: Props) {
  return (
    <Drawer
      title={`${anomaly.machine_id} · ${metricLabel(anomaly.metric)}`}
      badge={
        <span className={`mark mark-${anomaly.severity}`} style={{ marginTop: "0.3rem" }}>
          {anomaly.severity} severity
        </span>
      }
      onClose={onClose}
      footer={
        <button className="btn" onClick={onClose}>
          Close
        </button>
      }
    >
      <div className="panel" style={{ marginBottom: "1rem" }}>
        <div className="metric-label">{metricLabel(anomaly.metric)}</div>
        <div className="metric-value">
          {anomaly.value}
          <span className="unit">{METRIC_UNIT[anomaly.metric] ?? ""}</span>
        </div>
      </div>

      <dl className="dl">
        <dt>Machine</dt>
        <dd className="mono">{anomaly.machine_id}</dd>
        <dt>Timestamp</dt>
        <dd className="mono">{fmtStamp(anomaly.timestamp)}</dd>
        <dt>Severity</dt>
        <dd>
          <span className={`mark mark-${anomaly.severity}`}>{anomaly.severity}</span>
        </dd>
        <dt>Detector</dt>
        <dd className="mono">{anomaly.detector}</dd>
        <dt>Expected</dt>
        <dd className="mono">
          {anomaly.expected !== null
            ? `${anomaly.expected}${METRIC_UNIT[anomaly.metric] ?? ""}`
            : "threshold rule"}
        </dd>
        <dt>Deviation</dt>
        <dd className="mono">
          {anomaly.expected !== null
            ? `${anomaly.value > anomaly.expected ? "+" : ""}${(anomaly.value - anomaly.expected).toFixed(2)}${METRIC_UNIT[anomaly.metric] ?? ""}`
            : "n/a"}
        </dd>
      </dl>

      <div className="callout" style={{ marginTop: "1rem" }}>
        <span className="kpi-label">Reason</span>
        <p style={{ margin: "0.3rem 0 0" }}>{anomaly.reason}</p>
      </div>
    </Drawer>
  );
}

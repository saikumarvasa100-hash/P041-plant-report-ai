import Drawer from "./Drawer";
import type { Anomaly, MachineKPIs, PlantObservation } from "../services/api";
import { METRIC_UNIT, fmtTime, metricLabel, rankAnomalies } from "../lib/format";

interface TableProps {
  machines: MachineKPIs[];
  anomalies: Anomaly[];
  /** Raw observations, used for each unit's most recent recorded state. */
  observations?: PlantObservation[];
  onOpen: (m: MachineKPIs) => void;
}

interface DrawerProps {
  machine: MachineKPIs;
  anomalies: Anomaly[];
  observations?: PlantObservation[];
  onClose: () => void;
}

const STATUS_CLASS: Record<string, string> = {
  running: "mark-running",
  idle: "mark-idle",
  maintenance: "mark-maintenance",
  fault: "mark-fault",
};

/**
 * Latest recorded state per machine, from the raw observations.
 *
 * The period counters answer "how often was this unit faulted", not "what is
 * it doing now" — labelling a row FAULT because it faulted once in 48 periods
 * overstates the current condition. The last observation is the honest signal;
 * the counters are only a fallback when no observation is supplied.
 */
function latestStatusByMachine(
  observations: PlantObservation[] | undefined,
): Map<string, { status: string; timestamp: string }> {
  const latest = new Map<string, { status: string; timestamp: string }>();
  for (const o of observations ?? []) {
    const prev = latest.get(o.machine_id);
    if (!prev || o.timestamp > prev.timestamp) {
      latest.set(o.machine_id, { status: o.status, timestamp: o.timestamp });
    }
  }
  return latest;
}

function machineStatus(
  m: MachineKPIs,
  latest?: { status: string; timestamp: string },
): { label: string; cls: string; since?: string } {
  if (latest) {
    const s = latest.status.toLowerCase();
    const label = s.charAt(0).toUpperCase() + s.slice(1);
    return { label, cls: STATUS_CLASS[s] ?? "mark-idle", since: latest.timestamp };
  }
  if (m.fault_count > 0) return { label: "Fault", cls: "mark-fault" };
  if (m.maintenance_count > 0) return { label: "Maintenance", cls: "mark-maintenance" };
  if (m.idle_count > 0) return { label: "Idle", cls: "mark-idle" };
  return { label: "Running", cls: "mark-running" };
}

/** Full-width machine operations table with a detail drawer. */
export default function MachineOps({ machines, anomalies, observations, onOpen }: TableProps) {
  const countFor = (id: string) => anomalies.filter((a) => a.machine_id === id).length;
  const latest = latestStatusByMachine(observations);
  return (
    <div className="panel">
      <div className="panel-head">
        <h3 className="panel-title">Machine operations</h3>
        <span className="panel-note">
          {machines.length} units monitored · state from the latest observation
        </span>
      </div>
      <div className="table-scroll">
        <table>
          <thead>
            <tr>
              <th>Machine</th>
              <th>Status</th>
              <th className="num">OEE</th>
              <th className="num">Output</th>
              <th className="num">Efficiency</th>
              <th className="num">Energy</th>
              <th className="num">Downtime</th>
              <th className="num">MTBF</th>
              <th className="num">Anomalies</th>
              <th />
            </tr>
          </thead>
          <tbody>
            {machines.map((m) => {
              const s = machineStatus(m, latest.get(m.machine_id));
              const n = countFor(m.machine_id);
              return (
                <tr key={m.machine_id}>
                  <td>
                    <span className="mono" style={{ fontWeight: 600 }}>
                      {m.machine_id}
                    </span>
                  </td>
                  <td>
                    <span className={`mark ${s.cls}`}>{s.label}</span>
                    {s.since && <span className="cell-sub mono">{fmtTime(s.since)}</span>}
                  </td>
                  <td className="num">{m.oee_percent ? `${m.oee_percent.toFixed(1)}%` : "—"}</td>
                  <td className="num">{m.production.toLocaleString()}</td>
                  <td className="num">{m.average_efficiency.toFixed(1)}%</td>
                  <td className="num">{m.energy_kwh.toFixed(1)}</td>
                  <td className="num">{m.downtime_minutes.toFixed(1)}</td>
                  <td className="num">{m.mtbf_hours ? `${m.mtbf_hours.toFixed(1)}h` : "—"}</td>
                  <td className="num">{n}</td>
                  <td>
                    <button
                      className="row-btn"
                      onClick={() => onOpen(m)}
                      aria-label={`Inspect ${m.machine_id}`}
                    >
                      Inspect
                    </button>
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </div>
  );
}

/** Machine detail drawer, sourced entirely from the existing analytics payload. */
export function MachineDrawer({ machine, anomalies, observations, onClose }: DrawerProps) {
  const s = machineStatus(machine, latestStatusByMachine(observations).get(machine.machine_id));
  const mine = rankAnomalies(anomalies.filter((a) => a.machine_id === machine.machine_id));
  return (
    <Drawer
      title={machine.machine_id}
      badge={
        <span className={`mark ${s.cls}`} style={{ marginTop: "0.3rem" }}>
          {s.label}
          {s.since ? ` · last seen ${fmtTime(s.since)}` : ""}
        </span>
      }
      onClose={onClose}
      footer={
        <button className="btn" onClick={onClose}>
          Close
        </button>
      }
    >
      <div className="metrics-2" style={{ marginBottom: "1rem" }}>
        <div className="metric-cell">
          <div className="metric-label">Output</div>
          <div className="metric-value">
            {machine.production.toLocaleString()}
            <span className="unit">units</span>
          </div>
        </div>
        <div className="metric-cell">
          <div className="metric-label">Efficiency</div>
          <div className="metric-value">{machine.average_efficiency.toFixed(2)}%</div>
        </div>
        <div className="metric-cell">
          <div className="metric-label">Energy</div>
          <div className="metric-value">
            {machine.energy_kwh.toFixed(2)}
            <span className="unit">kWh</span>
          </div>
        </div>
        <div className="metric-cell">
          <div className="metric-label">Downtime</div>
          <div className="metric-value">
            {machine.downtime_minutes.toFixed(2)}
            <span className="unit">min</span>
          </div>
        </div>
      </div>

      <dl className="dl">
        <dt>OEE</dt>
        <dd className="mono">{machine.oee_percent ? `${machine.oee_percent.toFixed(2)}%` : "not reported"}</dd>
        <dt>Availability</dt>
        <dd className="mono">{machine.availability_percent ? `${machine.availability_percent.toFixed(2)}%` : "not reported"}</dd>
        <dt>Temp</dt>
        <dd className="mono">
          {machine.average_temperature_c.toFixed(2)}
          {METRIC_UNIT.temperature_c}
        </dd>
        <dt>Vibration</dt>
        <dd className="mono">
          {machine.average_vibration_mm_s.toFixed(2)}
          {METRIC_UNIT.vibration_mm_s}
        </dd>
        <dt>MTBF</dt>
        <dd className="mono">{machine.mtbf_hours ? `${machine.mtbf_hours.toFixed(2)} h` : "not reported"}</dd>
        <dt>MTTR</dt>
        <dd className="mono">{machine.mttr_minutes ? `${machine.mttr_minutes.toFixed(2)} min` : "not reported"}</dd>
        <dt>Status mix</dt>
        <dd className="mono">
          {machine.running_count} running · {machine.idle_count} idle · {machine.maintenance_count} maint ·{" "}
          {machine.fault_count} fault
        </dd>
      </dl>

      <h4 className="panel-title" style={{ margin: "1.2rem 0 0.4rem" }}>
        Anomaly log ({mine.length})
      </h4>
      {mine.length === 0 ? (
        <p className="panel-note">No anomalies recorded for this unit.</p>
      ) : (
        <div className="events">
          {mine.map((a, i) => (
            <div key={`${a.timestamp}-${i}`} className={`event ${a.severity}`} style={{ cursor: "default" }}>
              <span className={`mark mark-${a.severity}`}>{a.severity}</span>
              <span className="event-metric">
                {metricLabel(a.metric)}{" "}
                <span className="mono">
                  {a.value}
                  {METRIC_UNIT[a.metric] ?? ""}
                </span>
              </span>
              <span className="event-time">{fmtTime(a.timestamp)}</span>
            </div>
          ))}
        </div>
      )}
    </Drawer>
  );
}

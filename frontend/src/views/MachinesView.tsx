import MachineOps from "../components/MachineOps";
import type { AnalyticsReport, Anomaly, MachineKPIs, PlantObservation } from "../services/api";

interface Props {
  analytics: AnalyticsReport;
  observations: PlantObservation[];
  onOpenMachine: (m: MachineKPIs) => void;
  onOpenAnomaly: (a: Anomaly, trigger: HTMLElement) => void;
}

/** Unit-level condition view: status mix, output share, worst performers. */
export default function MachinesView({ analytics, observations, onOpenMachine, onOpenAnomaly }: Props) {
  const { machines, anomalies, plant } = analytics;
  const maxProduction = Math.max(...machines.map((m) => m.production), 1);
  const totalProduction = machines.reduce((a, m) => a + m.production, 0) || 1;
  const byAnomalies = [...machines].sort(
    (a, b) =>
      anomalies.filter((x) => x.machine_id === b.machine_id).length -
      anomalies.filter((x) => x.machine_id === a.machine_id).length,
  );
  const statusMix = [
    { label: "Running", value: plant.running_count },
    { label: "Idle", value: plant.idle_count },
    { label: "Maintenance", value: plant.maintenance_count },
    { label: "Fault", value: plant.fault_count },
  ];
  const maxMix = Math.max(...statusMix.map((s) => s.value), 1);

  return (
    <>
      <header className="view-head">
        <div>
          <h1 className="view-title">Machine operations</h1>
          <p className="view-sub">
            {machines.length} units · {plant.observation_count.toLocaleString()} observations
          </p>
        </div>
        <div className="view-facts">
          {statusMix.map((s) => (
            <div className="readout" key={s.label}>
              <span className="readout-label">{s.label}</span>
              <span className="readout-value">{s.value}</span>
            </div>
          ))}
        </div>
      </header>

      <section className="grid-12">
        <div className="col-12">
          <MachineOps machines={machines} anomalies={anomalies} observations={observations} onOpen={onOpenMachine} />
        </div>

        <div className="col-7">
          <div className="panel">
            <div className="panel-head">
              <h3 className="panel-title">Output share</h3>
              <span className="panel-note">Share of {totalProduction.toLocaleString()} units</span>
            </div>
            {machines.map((m) => {
              const share = (m.production / totalProduction) * 100;
              return (
                <div
                  key={m.machine_id}
                  style={{ display: "grid", gridTemplateColumns: "7.5rem 1fr 4.5rem", gap: "0.6rem", alignItems: "center", padding: "0.3rem 0" }}
                >
                  <span className="mono" style={{ fontSize: "0.8rem" }}>{m.machine_id}</span>
                  <span
                    style={{
                      display: "block",
                      height: "10px",
                      background: "var(--surface-2)",
                      border: "1px solid var(--line)",
                    }}
                  >
                    <span
                      style={{
                        display: "block",
                        height: "100%",
                        width: `${(m.production / maxProduction) * 100}%`,
                        background: "var(--accent)",
                      }}
                    />
                  </span>
                  <span className="mono" style={{ fontSize: "0.76rem", textAlign: "right" }}>
                    {share.toFixed(1)}%
                  </span>
                </div>
              );
            })}
          </div>
        </div>

        <div className="col-5">
          <div className="panel">
            <div className="panel-head">
              <h3 className="panel-title">Status distribution</h3>
              <span className="panel-note">Observation counts</span>
            </div>
            {statusMix.map((s) => (
              <div
                key={s.label}
                style={{ display: "grid", gridTemplateColumns: "7rem 1fr 3rem", gap: "0.6rem", alignItems: "center", padding: "0.28rem 0" }}
              >
                <span className="kpi-label">{s.label}</span>
                <span style={{ display: "block", height: "10px", background: "var(--surface-2)", border: "1px solid var(--line)" }}>
                  <span
                    style={{
                      display: "block",
                      height: "100%",
                      width: `${(s.value / maxMix) * 100}%`,
                      background:
                        s.label === "Fault"
                          ? "var(--critical)"
                          : s.label === "Maintenance"
                            ? "var(--warn)"
                            : s.label === "Running"
                              ? "var(--ok)"
                              : "var(--ink-3)",
                    }}
                  />
                </span>
                <span className="mono" style={{ fontSize: "0.78rem", textAlign: "right" }}>{s.value}</span>
              </div>
            ))}
          </div>
        </div>

        <div className="col-12">
          <div className="panel">
            <div className="panel-head">
              <h3 className="panel-title">Units by anomaly count</h3>
              <span className="panel-note">Most affected first</span>
            </div>
            <div className="table-scroll">
              <table>
                <thead>
                  <tr>
                    <th>Machine</th>
                    <th className="num">Anomalies</th>
                    <th className="num">Critical</th>
                    <th className="num">Downtime</th>
                    <th>Most recent event</th>
                    <th />
                  </tr>
                </thead>
                <tbody>
                  {byAnomalies.map((m) => {
                    const mine = anomalies.filter((x) => x.machine_id === m.machine_id);
                    const latest = [...mine].sort((a, b) => b.timestamp.localeCompare(a.timestamp))[0];
                    return (
                      <tr key={m.machine_id}>
                        <td className="mono" style={{ fontWeight: 600 }}>{m.machine_id}</td>
                        <td className="num">{mine.length}</td>
                        <td className="num">{mine.filter((x) => x.severity === "critical").length}</td>
                        <td className="num">{m.downtime_minutes.toFixed(1)}</td>
                        <td>
                          {latest ? (
                            <button
                              className="row-btn"
                              onClick={(e) => onOpenAnomaly(latest, e.currentTarget)}
                            >
                              <span className={`mark mark-${latest.severity}`}>{latest.severity}</span>{" "}
                              {latest.metric.replace(/_/g, " ")}
                            </button>
                          ) : (
                            <span className="muted">None</span>
                          )}
                        </td>
                        <td>
                          <button
                            className="row-btn"
                            onClick={() => onOpenMachine(m)}
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
        </div>
      </section>
    </>
  );
}

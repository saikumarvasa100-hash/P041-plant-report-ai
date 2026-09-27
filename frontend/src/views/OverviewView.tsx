import EventStream from "../components/EventStream";
import HealthPanel from "../components/HealthPanel";
import KpiCard from "../components/KpiCard";
import MachineOps from "../components/MachineOps";
import TrendChart from "../components/TrendChart";
import { severityCounts } from "../lib/format";
import type { AnalyticsReport, Anomaly, MachineKPIs, PlantObservation } from "../services/api";
import { METRIC, buildSeries, criticalCount, deltaOf, fmtDuration, fmtPeriod, markersFor, trendOf } from "./viewData";

interface Props {
  analytics: AnalyticsReport;
  observations: PlantObservation[];
  onOpenAnomaly: (a: Anomaly, trigger: HTMLElement) => void;
  onOpenMachine: (m: MachineKPIs) => void;
  onGoAnalytics: () => void;
}

export default function OverviewView({
  analytics,
  observations,
  onOpenAnomaly,
  onOpenMachine,
  onGoAnalytics,
}: Props) {
  const p = analytics.plant;
  const s = buildSeries(observations);
  const crit = criticalCount(analytics);
  const period = fmtPeriod(analytics);
  const prodTrend = trendOf(analytics, METRIC.production);

  return (
    <>
      <header className="view-head">
        <div>
          <h1 className="view-title">Operations overview</h1>
          <p className="view-sub">
            {period.date} · {period.span}
          </p>
        </div>
        <div className="view-facts">
          <div className="readout">
            <span className="readout-label">Observations</span>
            <span className="readout-value">{p.observation_count.toLocaleString()}</span>
          </div>
          <div className="readout">
            <span className="readout-label">Machines</span>
            <span className="readout-value">{p.machine_count}</span>
          </div>
          <div className="readout">
            <span className="readout-label">Window</span>
            <span className="readout-value">
              {analytics.period ? fmtDuration(analytics.period.duration_minutes) : "—"}
            </span>
          </div>
        </div>
      </header>

      <section className="kpi-strip" aria-label="Key plant indicators">
        <KpiCard
          label="Production"
          value={p.total_production.toLocaleString()}
          unit="units"
          delta={deltaOf(analytics, METRIC.production)}
          spark={s.production.map((x) => x.y)}
          tone="accent"
        />
        <KpiCard
          label="Efficiency"
          value={`${p.average_efficiency.toFixed(2)}%`}
          unit="average"
          delta={deltaOf(analytics, METRIC.efficiency)}
          spark={s.efficiency.map((x) => x.y)}
          tone="ok"
        />
        <KpiCard
          label="Energy"
          value={p.total_energy_kwh.toLocaleString()}
          unit="kWh"
          delta={deltaOf(analytics, METRIC.energy)}
          spark={s.energy.map((x) => x.y)}
        />
        <KpiCard
          label="Downtime"
          value={p.total_downtime_minutes.toLocaleString()}
          unit="min"
          delta={deltaOf(analytics, METRIC.downtime)}
          spark={s.downtime.map((x) => x.y)}
          tone={p.fault_count > 0 ? "warn" : "neutral"}
        />
        <KpiCard
          label="Anomalies"
          value={String(analytics.anomalies.length)}
          unit={crit > 0 ? `${crit} critical` : "none critical"}
          tone={crit > 0 ? "critical" : "ok"}
          severity={severityCounts(analytics.anomalies)}
        />
      </section>

      <section className="grid-12">
        <div className="col-8">
          <TrendChart
            title="Production output"
            points={s.production}
            tone="accent"
            height={300}
            markers={markersFor(analytics, METRIC.production)}
            aside={
              prodTrend ? (
                <span className="panel-note mono">
                  {prodTrend.direction.toUpperCase()} {prodTrend.change_percent > 0 ? "+" : ""}
                  {prodTrend.change_percent}%
                </span>
              ) : null
            }
          />
        </div>
        <div className="col-4">
          <HealthPanel anomalies={analytics.anomalies} />
        </div>

        <div className="col-4">
          <TrendChart
            title="Efficiency"
            points={s.efficiency}
            tone="ok"
            unit="%"
            height={150}
            compact
            markers={markersFor(analytics, METRIC.efficiency)}
          />
        </div>
        <div className="col-4">
          <TrendChart
            title="Energy"
            points={s.energy}
            tone="warn"
            unit=" kWh"
            height={150}
            compact
            markers={markersFor(analytics, METRIC.energy)}
          />
        </div>
        <div className="col-4">
          <TrendChart
            title="Downtime"
            points={s.downtime}
            tone="critical"
            unit=" min"
            height={150}
            compact
            markers={markersFor(analytics, METRIC.downtime)}
          />
        </div>
      </section>

      <section className="grid-12">
        <div className="col-7">
          <MachineOps
            machines={analytics.machines}
            anomalies={analytics.anomalies}
            observations={observations}
            onOpen={onOpenMachine}
          />
        </div>
        <div className="col-5">
          <EventStream
            anomalies={analytics.anomalies}
            limit={6}
            onOpen={(a, t) => onOpenAnomaly(a, t)}
          />
          <div style={{ marginTop: "1rem" }}>
            <button className="btn" onClick={onGoAnalytics}>
              Open full analytics
            </button>
          </div>
        </div>
      </section>
    </>
  );
}

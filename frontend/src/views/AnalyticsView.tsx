import TrendChart from "../components/TrendChart";
import type { AnalyticsReport, PlantObservation } from "../services/api";
import { METRIC, buildSeries, deltaOf, fmtPeriod, markersFor, trendOf } from "./viewData";

interface Props {
  analytics: AnalyticsReport;
  observations: PlantObservation[];
}

/** Full monitoring screen: lead production trace plus condition channels. */
export default function AnalyticsView({ analytics, observations }: Props) {
  const s = buildSeries(observations);
  const p = analytics.plant;
  const period = fmtPeriod(analytics);

  const channels = [
    { title: "Efficiency", points: s.efficiency, metric: METRIC.efficiency, tone: "ok" as const, unit: "%", height: 200 },
    { title: "Energy", points: s.energy, metric: METRIC.energy, tone: "warn" as const, unit: " kWh", height: 200 },
    { title: "Temperature", points: s.temperature, metric: METRIC.temperature, tone: "critical" as const, unit: "°C", height: 200 },
    { title: "Vibration", points: s.vibration, metric: METRIC.vibration, tone: "steel" as const, unit: " mm/s", height: 200 },
    { title: "Downtime", points: s.downtime, metric: METRIC.downtime, tone: "ink" as const, unit: " min", height: 200 },
  ];

  return (
    <>
      <header className="view-head">
        <div>
          <h1 className="view-title">Signal analytics</h1>
          <p className="view-sub">
            {period.date} · {period.span} · every figure from the deterministic analytics stage
          </p>
        </div>
        <div className="view-facts">
          <div className="readout">
            <span className="readout-label">OEE</span>
            <span className="readout-value">
              {p.oee_percent ? `${p.oee_percent.toFixed(2)}%` : "—"}
            </span>
          </div>
          <div className="readout">
            <span className="readout-label">Availability</span>
            <span className="readout-value">
              {p.availability_percent ? `${p.availability_percent.toFixed(2)}%` : "—"}
            </span>
          </div>
          <div className="readout">
            <span className="readout-label">Quality</span>
            <span className="readout-value">
              {p.quality_percent ? `${p.quality_percent.toFixed(2)}%` : "—"}
            </span>
          </div>
          <div className="readout">
            <span className="readout-label">Energy intensity</span>
            <span className="readout-value">
              {p.energy_intensity ? `${p.energy_intensity.toFixed(1)} kWh/unit` : "—"}
            </span>
          </div>
        </div>
      </header>

      <TrendChart
        title="Production output"
        points={s.production}
        tone="accent"
        height={320}
        markers={markersFor(analytics, METRIC.production)}
        aside={
          <span className="panel-note mono">
            {trendOf(analytics, METRIC.production)?.direction.toUpperCase() ?? "—"}
          </span>
        }
      />

      <section className="grid-12">
        {channels.slice(0, 2).map((c) => (
          <div className="col-6" key={c.title}>
            <TrendChart
              title={c.title}
              points={c.points}
              tone={c.tone}
              unit={c.unit}
              height={c.height}
              markers={markersFor(analytics, c.metric)}
              aside={
                <span className="panel-note mono">
                  {(() => {
                    const d = deltaOf(analytics, c.metric);
                    return d ? `${d.direction === "increasing" ? "↑" : d.direction === "decreasing" ? "↓" : "→"} ${d.change_percent > 0 ? "+" : ""}${d.change_percent}%` : "—";
                  })()}
                </span>
              }
            />
          </div>
        ))}
        {channels.slice(2, 4).map((c) => (
          <div className="col-6" key={c.title}>
            <TrendChart
              title={c.title}
              points={c.points}
              tone={c.tone}
              unit={c.unit}
              height={c.height}
              markers={markersFor(analytics, c.metric)}
            />
          </div>
        ))}
        <div className="col-12">
          <TrendChart
            title={channels[4].title}
            points={channels[4].points}
            tone={channels[4].tone}
            unit={channels[4].unit}
            height={200}
            markers={markersFor(analytics, METRIC.downtime)}
          />
        </div>
      </section>

      <div className="panel">
        <div className="panel-head">
          <h3 className="panel-title">Backend trend analysis</h3>
          <span className="panel-note">Half-split comparison computed server-side</span>
        </div>
        <div className="table-scroll">
          <table>
            <thead>
              <tr>
                <th>Metric</th>
                <th>Direction</th>
                <th className="num">Change</th>
                <th className="num">Strength</th>
                <th className="num">Earlier mean</th>
                <th className="num">Later mean</th>
                <th className="num">Samples</th>
                <th>Method</th>
              </tr>
            </thead>
            <tbody>
              {analytics.trends.map((t) => (
                <tr key={t.metric}>
                  <td className="mono">{t.metric}</td>
                  <td>
                    <span
                      className={`mark mark-${t.direction === "increasing" ? "ok" : t.direction === "decreasing" ? "critical" : "idle"}`}
                    >
                      {t.direction}
                    </span>
                  </td>
                  <td className="num">
                    {t.change_percent > 0 ? "+" : ""}
                    {t.change_percent}%
                  </td>
                  <td className="num">{t.strength.toFixed(3)}</td>
                  <td className="num">{t.earlier_mean.toFixed(2)}</td>
                  <td className="num">{t.later_mean.toFixed(2)}</td>
                  <td className="num">{t.observation_count}</td>
                  <td className="mono">{t.method}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </>
  );
}

import type {
  AnalyticsReport,
  Anomaly,
  DemoParams,
  PlantObservation,
  TrendResult,
} from "../services/api";
import type { SeriesPoint } from "../components/TrendChart";

export type ViewId = "overview" | "analytics" | "machines" | "anomalies" | "reports" | "data";

export interface ViewDef {
  id: ViewId;
  num: string;
  label: string;
  title: string;
  sub: string;
}

export const VIEWS: ViewDef[] = [
  { id: "overview", num: "01", label: "Overview", title: "Operations overview", sub: "Plant performance at a glance" },
  { id: "analytics", num: "02", label: "Analytics", title: "Signal analytics", sub: "Production, efficiency, energy and condition trends" },
  { id: "machines", num: "03", label: "Machines", title: "Machine operations", sub: "Per-unit output, condition and anomaly history" },
  { id: "anomalies", num: "04", label: "Anomalies", title: "Anomaly investigation", sub: "Threshold and statistical detections with evidence" },
  { id: "reports", num: "05", label: "AI reports", title: "Report workstation", sub: "LLM narrative grounded in the analytics above" },
  { id: "data", num: "06", label: "Data", title: "Data ingestion", sub: "Analyse your own plant CSV" },
];

/** Mean-per-timestamp series from raw observations (display aggregation only). */
export function seriesOf(
  obs: PlantObservation[],
  pick: (o: PlantObservation) => number,
): SeriesPoint[] {
  const buckets = new Map<string, number[]>();
  for (const o of [...obs].sort((a, b) => a.timestamp.localeCompare(b.timestamp))) {
    const arr = buckets.get(o.timestamp) ?? [];
    arr.push(pick(o));
    buckets.set(o.timestamp, arr);
  }
  return [...buckets.entries()].map(([x, vals]) => ({
    x,
    y: vals.reduce((a, b) => a + b, 0) / vals.length,
  }));
}

export const METRIC = {
  production: "production_count",
  efficiency: "efficiency_percent",
  energy: "energy_consumption_kwh",
  downtime: "downtime_minutes",
  temperature: "temperature_c",
  vibration: "vibration_mm_s",
} as const;

export function buildSeries(obs: PlantObservation[]) {
  return {
    production: seriesOf(obs, (o) => o.production_count),
    efficiency: seriesOf(obs, (o) => o.efficiency_percent),
    energy: seriesOf(obs, (o) => o.energy_consumption_kwh),
    downtime: seriesOf(obs, (o) => o.downtime_minutes),
    temperature: seriesOf(obs, (o) => o.temperature_c),
    vibration: seriesOf(obs, (o) => o.vibration_mm_s),
  };
}

/** Trend markers for one metric, straight from the backend anomaly list. */
export function markersFor(
  analytics: AnalyticsReport | null,
  metric: string,
): { x: string; severity: Anomaly["severity"] }[] {
  return (analytics?.anomalies ?? [])
    .filter((a) => a.metric === metric)
    .map((a) => ({ x: a.timestamp, severity: a.severity }));
}

export function trendOf(a: AnalyticsReport | null, metric: string): TrendResult | undefined {
  return a?.trends.find((t) => t.metric === metric);
}

export function deltaOf(a: AnalyticsReport | null, metric: string) {
  const t = trendOf(a, metric);
  if (!t) return null;
  return { direction: t.direction, change_percent: t.change_percent };
}

export function criticalCount(a: AnalyticsReport | null): number {
  return a?.anomalies.filter((x) => x.severity === "critical").length ?? 0;
}

export function fmtPeriod(a: AnalyticsReport | null): { date: string; span: string } {
  if (!a?.period) return { date: "—", span: "—" };
  const s = new Date(a.period.start_timestamp);
  const e = new Date(a.period.end_timestamp);
  const hhmm = (d: Date) =>
    `${String(d.getHours()).padStart(2, "0")}:${String(d.getMinutes()).padStart(2, "0")}`;
  return {
    date: s
      .toLocaleDateString("en-GB", { day: "2-digit", month: "short", year: "numeric" })
      .toUpperCase(),
    span: `${hhmm(s)} — ${hhmm(e)}`,
  };
}

export function fmtDuration(minutes: number): string {
  const h = Math.floor(minutes / 60);
  const m = Math.round(minutes % 60);
  return h > 0 ? `${h}h ${m}m` : `${m}m`;
}

export function sourceLabel(source: "simulator" | "upload" | null, p: DemoParams, name: string | null): string {
  if (source === "upload") return name ? `Uploaded · ${name}` : "Uploaded";
  if (source === "simulator") return `Simulated · ${p.machines}/${p.observations} · seed ${p.seed}`;
  return "—";
}

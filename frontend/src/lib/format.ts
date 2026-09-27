/** Shared formatting and ranking helpers.
 *
 * These live outside the component files so the components can export only
 * components (cleaner fast-refresh boundaries) and so the anomaly vocabulary
 * is defined in exactly one place.
 */

import type { Anomaly } from "../services/api";

export const SEV_RANK: Record<Anomaly["severity"], number> = {
  critical: 0,
  high: 1,
  medium: 2,
  low: 3,
};

export const SEVERITIES: Anomaly["severity"][] = ["critical", "high", "medium", "low"];

/** Unit suffix per backend metric key, so values read as measurements. */
export const METRIC_UNIT: Record<string, string> = {
  temperature_c: "°C",
  vibration_mm_s: " mm/s",
  downtime_minutes: " min",
  efficiency_percent: "%",
  energy_consumption_kwh: " kWh",
  production_count: " units",
};

export function metricLabel(metric: string): string {
  return metric.replace(/_/g, " ");
}

export function fmtTime(iso: string): string {
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return iso;
  return `${String(d.getHours()).padStart(2, "0")}:${String(d.getMinutes()).padStart(2, "0")}`;
}

export function fmtStamp(iso: string): string {
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return iso;
  return `${String(d.getDate()).padStart(2, "0")}/${String(d.getMonth() + 1).padStart(2, "0")} ${fmtTime(iso)}`;
}

/** Highest-priority events first: severity, then most recent. */
export function rankAnomalies(anomalies: Anomaly[]): Anomaly[] {
  return [...anomalies].sort(
    (a, b) => SEV_RANK[a.severity] - SEV_RANK[b.severity] || b.timestamp.localeCompare(a.timestamp),
  );
}

export function severityCounts(anomalies: Anomaly[]): Record<Anomaly["severity"], number> {
  const counts: Record<Anomaly["severity"], number> = { critical: 0, high: 0, medium: 0, low: 0 };
  for (const a of anomalies) counts[a.severity] += 1;
  return counts;
}

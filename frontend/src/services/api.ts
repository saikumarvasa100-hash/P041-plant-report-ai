/** Typed client for the Plant Report AI FastAPI backend.
 *
 * Python remains the source of truth: this module only fetches and displays.
 * Base URL comes from VITE_API_BASE_URL (see .env.example).
 */

const BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8001";

export interface PlantKPIs {
  observation_count: number;
  machine_count: number;
  total_production: number;
  average_efficiency: number;
  total_energy_kwh: number;
  total_downtime_minutes: number;
  average_temperature_c: number;
  average_vibration_mm_s: number;
  running_count: number;
  idle_count: number;
  maintenance_count: number;
  fault_count: number;
  oee_percent?: number;
  availability_percent?: number;
  performance_percent?: number;
  quality_percent?: number;
  energy_intensity?: number;
  mtbf_hours?: number;
  mttr_minutes?: number;
}

export interface MachineKPIs {
  machine_id: string;
  observation_count: number;
  production: number;
  average_efficiency: number;
  energy_kwh: number;
  downtime_minutes: number;
  average_temperature_c: number;
  average_vibration_mm_s: number;
  running_count: number;
  idle_count: number;
  maintenance_count: number;
  fault_count: number;
  oee_percent?: number;
  availability_percent?: number;
  performance_percent?: number;
  quality_percent?: number;
  energy_intensity?: number;
  mtbf_hours?: number;
  mttr_minutes?: number;
}

export interface TrendResult {
  metric: string;
  direction: "increasing" | "decreasing" | "stable";
  change_percent: number;
  strength: number;
  earlier_mean: number;
  later_mean: number;
  start_timestamp: string;
  end_timestamp: string;
  observation_count: number;
  method: string;
}

export interface Anomaly {
  machine_id: string;
  timestamp: string;
  metric: string;
  value: number;
  expected: number | null;
  severity: "low" | "medium" | "high" | "critical";
  reason: string;
  detector: string;
}

export interface ReportingPeriod {
  start_timestamp: string;
  end_timestamp: string;
  duration_minutes: number;
  observation_count: number;
}

export interface AnalyticsReport {
  period: ReportingPeriod | null;
  plant: PlantKPIs;
  machines: MachineKPIs[];
  trends: TrendResult[];
  anomalies: Anomaly[];
  summaries: string[];
}

export interface PlantObservation {
  timestamp: string;
  machine_id: string;
  production_count: number;
  energy_consumption_kwh: number;
  efficiency_percent: number;
  temperature_c: number;
  vibration_mm_s: number;
  downtime_minutes: number;
  status: string;
}

export interface GeneratedReport {
  report_type: string;
  generated_at: string;
  reporting_period: string;
  content: string;
  analytics_summary: {
    total_production: number;
    average_efficiency: number;
    total_energy_kwh: number;
    total_downtime_minutes: number;
    anomaly_count: number;
    machine_count: number;
  };
  numbers_verified: boolean;
  provider: string;
  model: string;
}

export type ReportType = "daily" | "weekly" | "monthly";

async function get<T>(path: string, signal?: AbortSignal): Promise<T> {
  const resp = await fetch(`${BASE_URL}${path}`, { signal });
  if (!resp.ok) {
    const shortPath = path.split("?")[0]; // keep messages wrappable on mobile
    throw new Error(`GET ${shortPath} failed: ${resp.status} ${resp.statusText}`);
  }
  return resp.json() as Promise<T>;
}

export interface DemoParams {
  machines: number;
  observations: number;
  seed: number;
}

export const DEMO_PARAMS: DemoParams = { machines: 4, observations: 48, seed: 7 };

function query(p: DemoParams): string {
  return `machines=${p.machines}&observations=${p.observations}&seed=${p.seed}`;
}

export function fetchAnalytics(p: DemoParams = DEMO_PARAMS, signal?: AbortSignal): Promise<AnalyticsReport> {
  return get<AnalyticsReport>(`/api/v1/analytics/sample?${query(p)}`, signal);
}

export function fetchObservations(p: DemoParams = DEMO_PARAMS, signal?: AbortSignal): Promise<PlantObservation[]> {
  return get<PlantObservation[]>(`/api/v1/data/sample?${query(p)}`, signal);
}

export interface ProviderStatus {
  provider: string;
  mode: "demo" | "live" | "unconfigured";
  model?: string;
}

export function fetchReportStatus(signal?: AbortSignal): Promise<ProviderStatus> {
  return get<ProviderStatus>("/api/v1/reports/status", signal);
}

export function fetchSampleReport(
  p: DemoParams = DEMO_PARAMS,
  reportType: ReportType = "daily",
  signal?: AbortSignal,
): Promise<GeneratedReport> {
  return get<GeneratedReport>(`/api/v1/reports/sample?report_type=${reportType}&${query(p)}`, signal);
}

export interface UploadProfile {
  id: string;
  label: string;
}

export interface UploadResult {
  filename: string;
  profile: string;
  csv_rows: number;
  observation_count: number;
  derived_fields: string[];
  observations: PlantObservation[];
  analytics: AnalyticsReport;
}

export async function fetchUploadProfiles(signal?: AbortSignal): Promise<UploadProfile[]> {
  return get<UploadProfile[]>("/api/v1/data/profiles", signal);
}

export async function uploadPlantCsv(file: File, profile: string): Promise<UploadResult> {
  const form = new FormData();
  form.append("file", file);
  const resp = await fetch(`${BASE_URL}/api/v1/data/upload?profile=${encodeURIComponent(profile)}`, {
    method: "POST",
    body: form,
  });
  if (!resp.ok) {
    const detail = await resp.text();
    throw new Error(`Upload failed (${resp.status}): ${detail.slice(0, 300)}`);
  }
  return resp.json() as Promise<UploadResult>;
}

export async function generateReportFromAnalytics(
  analytics: AnalyticsReport,
  reportType: ReportType,
): Promise<GeneratedReport> {
  const resp = await fetch(`${BASE_URL}/api/v1/reports/from-analytics`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ analytics, report_type: reportType }),
  });
  if (!resp.ok) {
    const detail = await resp.text();
    throw new Error(`Report generation failed (${resp.status}): ${detail.slice(0, 200)}`);
  }
  return resp.json() as Promise<GeneratedReport>;
}

export async function generateReport(
  reportType: ReportType,
  p: DemoParams = DEMO_PARAMS,
): Promise<GeneratedReport> {
  const resp = await fetch(`${BASE_URL}/api/v1/reports/generate`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ report_type: reportType, ...p }),
  });
  if (!resp.ok) {
    const detail = await resp.text();
    throw new Error(`Report generation failed (${resp.status}): ${detail.slice(0, 200)}`);
  }
  return resp.json() as Promise<GeneratedReport>;
}

export async function exportReportHtml(
  report: GeneratedReport,
): Promise<string> {
  const resp = await fetch(`${BASE_URL}/api/v1/reports/export/html`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      title: `${report.report_type.toUpperCase()} Plant Performance Report`,
      content: report.content,
      model: report.model,
      numbers_verified: report.numbers_verified,
      reporting_period: report.reporting_period,
    }),
  });
  if (!resp.ok) {
    throw new Error(`HTML Export failed (${resp.status})`);
  }
  return resp.text();
}

export interface KpiDelta {
  direction: "increasing" | "decreasing" | "stable";
  change_percent: number;
}

interface Props {
  label: string;
  value: string;
  unit?: string;
  /** Contextual line under the value, e.g. "18 critical". */
  note?: string;
  /** Backend trend delta. Never computed here. */
  delta?: KpiDelta | null;
  /** Top-rule colour role. */
  tone?: "neutral" | "accent" | "ok" | "warn" | "critical";
  /** Display-only sparkline of already-fetched observations. */
  spark?: number[];
  /** Severity distribution strip, used where a sparkline would not apply. */
  severity?: { critical: number; high: number; medium: number; low: number };
  compact?: boolean;
}

const TONE_CLASS = {
  neutral: "",
  accent: "kpi-accent",
  ok: "kpi-ok",
  warn: "kpi-high",
  critical: "kpi-critical",
} as const;

function deltaText(d: KpiDelta): string {
  const sign = d.change_percent > 0 ? "+" : "";
  const arrow = d.direction === "increasing" ? "↑" : d.direction === "decreasing" ? "↓" : "→";
  return `${arrow} ${sign}${d.change_percent}%`;
}

function sparkPath(values: number[]): { line: string; area: string } | null {
  if (values.length < 2) return null;
  const min = Math.min(...values);
  const max = Math.max(...values);
  const span = max - min || 1;
  const n = values.length;
  const pts = values.map(
    (v, i) => `${((i / (n - 1)) * 100).toFixed(2)},${(20 - ((v - min) / span) * 18).toFixed(2)}`,
  );
  return { line: pts.join(" "), area: `0,22 ${pts.join(" ")} 100,22` };
}

/**
 * Telemetry readout. The number is the largest element on the panel because it
 * is the thing an operator reads across a room; the unit, note and backend
 * trend delta sit beneath it at legend size.
 */
export default function KpiCard({
  label,
  value,
  unit,
  note,
  delta,
  tone = "neutral",
  spark,
  severity,
  compact = false,
}: Props) {
  const s = spark ? sparkPath(spark) : null;
  const sevTotal = severity
    ? severity.critical + severity.high + severity.medium + severity.low
    : 0;
  return (
    <div className={`kpi ${TONE_CLASS[tone]}`}>
      <span className="kpi-label">{label}</span>
      <div className={`kpi-value${compact ? " sm" : ""}`}>{value}</div>
      <div className="kpi-foot">
        <span>
          {unit}
          {note ? ` · ${note}` : ""}
        </span>
        {delta && <span className={`kpi-delta ${delta.direction === "increasing" ? "up" : delta.direction === "decreasing" ? "down" : "flat"}`}>{deltaText(delta)}</span>}
      </div>
      {s && (
        <svg className="spark" viewBox="0 0 100 22" preserveAspectRatio="none" aria-hidden="true">
          <polygon points={s.area} fill="var(--ink-3)" opacity="0.08" />
          <polyline
            points={s.line}
            fill="none"
            stroke="var(--ink-3)"
            strokeWidth="1.1"
            opacity="0.7"
            vectorEffect="non-scaling-stroke"
          />
        </svg>
      )}
      {severity && sevTotal > 0 && (
        <div className="spark-sev">
          {(["critical", "high", "medium", "low"] as const).map((k) =>
            severity[k] > 0 ? (
              <span
                key={k}
                className={`spark-sev-seg ${k}`}
                style={{ flexGrow: severity[k] }}
                title={`${severity[k]} ${k}`}
              />
            ) : null,
          )}
        </div>
      )}
    </div>
  );
}

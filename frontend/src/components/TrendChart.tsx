/** Dependency-free SVG line chart for real backend series. */

import { useRef, useState } from "react";

export interface SeriesPoint {
  x: string;
  y: number;
}

export interface TrendMarker {
  /** ISO timestamp of a backend anomaly; snapped to the nearest series point. */
  x: string;
  severity: "low" | "medium" | "high" | "critical";
}

interface Props {
  title: string;
  points: SeriesPoint[];
  /** Unit suffix for axis ticks and the tooltip. */
  unit?: string;
  /** Semantic line colour token name (not a raw hex) so theming stays central. */
  tone?: "accent" | "ok" | "warn" | "critical" | "steel" | "ink";
  markers?: TrendMarker[];
  /** Plot height in px. The production monitor is the tallest panel. */
  height?: number;
  /** Compact panels drop the y-axis labels to save vertical space. */
  compact?: boolean;
  /** Optional right-aligned headline figure, e.g. the backend trend delta. */
  aside?: React.ReactNode;
  /** Legend entries for anomaly markers present in this series. */
  showMarkerLegend?: boolean;
}

const W = 640;
const PAD_L = 46;
const PAD_R = 12;
const PAD_T = 10;
const PAD_B = 22;

const TONE_VAR = {
  accent: "var(--accent)",
  ok: "var(--ok)",
  warn: "var(--warn)",
  critical: "var(--critical)",
  steel: "var(--steel)",
  ink: "var(--ink)",
} as const;

const SEV_VAR = {
  critical: "var(--critical)",
  high: "var(--warn)",
  medium: "var(--steel)",
  low: "var(--ink-3)",
} as const;

const SEV_ORDER: TrendMarker["severity"][] = ["critical", "high", "medium", "low"];

function fmtClock(iso: string): string {
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return iso;
  return `${String(d.getHours()).padStart(2, "0")}:${String(d.getMinutes()).padStart(2, "0")}`;
}

function fmtStamp(iso: string): string {
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return iso;
  const mm = String(d.getMonth() + 1).padStart(2, "0");
  const dd = String(d.getDate()).padStart(2, "0");
  return `${dd}/${mm} ${fmtClock(iso)}`;
}

function nearestIndex(points: SeriesPoint[], x: string): number {
  const t = Date.parse(x);
  if (Number.isNaN(t)) return 0;
  let best = 0;
  let bestD = Infinity;
  points.forEach((p, i) => {
    const d = Math.abs(Date.parse(p.x) - t);
    if (d < bestD) {
      bestD = d;
      best = i;
    }
  });
  return best;
}

export default function TrendChart({
  title,
  points,
  unit = "",
  tone = "accent",
  markers = [],
  height = 200,
  compact = false,
  aside,
  showMarkerLegend = true,
}: Props) {
  const svgRef = useRef<SVGSVGElement | null>(null);
  const [hover, setHover] = useState<number | null>(null);
  const stroke = TONE_VAR[tone];

  if (points.length === 0) {
    return (
      <div className="panel">
        <div className="panel-head">
          <h3 className="panel-title">{title}</h3>
        </div>
        <p className="panel-note">No observations in range.</p>
      </div>
    );
  }

  const H = height;
  const ys = points.map((p) => p.y);
  const rawMin = Math.min(...ys);
  const rawMax = Math.max(...ys);
  const pad = (rawMax - rawMin) * 0.12 || Math.abs(rawMax) * 0.1 || 1;
  const min = rawMin - pad;
  const max = rawMax + pad;
  const span = max - min || 1;
  const stepX = points.length > 1 ? (W - PAD_L - PAD_R) / (points.length - 1) : 0;
  const toXY = (i: number, y: number): [number, number] => [
    PAD_L + i * stepX,
    PAD_T + (1 - (y - min) / span) * (H - PAD_T - PAD_B),
  ];
  const path = points.map((p, i) => `${i === 0 ? "M" : "L"}${toXY(i, p.y).join(",")}`).join(" ");
  const baseY = H - PAD_B;
  const area = `${path} L${toXY(points.length - 1, points[points.length - 1].y)[0]},${baseY} L${PAD_L},${baseY} Z`;
  const last = points[points.length - 1];
  const [lx, ly] = toXY(points.length - 1, last.y);

  const yTicks = compact ? 2 : 4;
  const gridF = Array.from({ length: yTicks + 1 }, (_, i) => i / yTicks);
  // Label a few x positions, always including first and last.
  const xLabelAt = new Set<number>([0, points.length - 1]);
  const xEvery = Math.max(1, Math.round(points.length / (compact ? 3 : 5)));
  for (let i = 0; i < points.length; i += xEvery) xLabelAt.add(i);

  function onMove(e: React.MouseEvent<SVGSVGElement>) {
    const rect = svgRef.current?.getBoundingClientRect();
    if (!rect || rect.width === 0) return;
    const fx = ((e.clientX - rect.left) / rect.width) * W;
    const idx = Math.round((fx - PAD_L) / stepX);
    setHover(Math.max(0, Math.min(points.length - 1, idx)));
  }

  const probe = hover !== null ? toXY(hover, points[hover].y) : null;
  const presentSev = SEV_ORDER.filter((s) => markers.some((m) => m.severity === s));

  return (
    <div className="panel chart">
      <div className="panel-head">
        <h3 className="panel-title">{title}</h3>
        {aside}
      </div>
      <div className="chart-plot">
        <svg
          ref={svgRef}
          viewBox={`0 0 ${W} ${H}`}
          style={{ height }}
          role="img"
          aria-label={`${title}: ${points.length} points from ${fmtStamp(points[0].x)} to ${fmtStamp(last.x)}. Latest ${last.y.toFixed(2)}${unit}, range ${rawMin.toFixed(2)} to ${rawMax.toFixed(2)}${unit}.`}
          onMouseMove={onMove}
          onMouseLeave={() => setHover(null)}
        >
          {gridF.map((f) => {
            const y = PAD_T + f * (H - PAD_T - PAD_B);
            const v = max - f * span;
            return (
              <g key={f}>
                <line x1={PAD_L} x2={W - PAD_R} y1={y} y2={y} className="chart-grid-line" />
                {!compact && (
                  <text x={PAD_L - 6} y={y + 3} textAnchor="end" className="chart-value-tick">
                    {v.toFixed(span < 10 ? 1 : 0)}
                  </text>
                )}
              </g>
            );
          })}
          <line x1={PAD_L} x2={W - PAD_R} y1={baseY} y2={baseY} className="chart-axis-line" />

          <path d={area} fill={stroke} className="chart-area" />
          <path d={path} className="chart-line" stroke={stroke} />

          {markers.map((m, i) => {
            const [cx, cy] = toXY(nearestIndex(points, m.x), points[nearestIndex(points, m.x)].y);
            return (
              <circle
                key={`${m.x}-${i}`}
                cx={cx}
                cy={cy}
                r={3.4}
                className="chart-anomaly"
                stroke={SEV_VAR[m.severity]}
              />
            );
          })}

          {probe && <line x1={probe[0]} x2={probe[0]} y1={PAD_T} y2={baseY} className="chart-probe" />}
          {probe && <circle cx={probe[0]} cy={probe[1]} r={3.6} fill={stroke} />}
          <circle cx={lx} cy={ly} r={3.6} fill={stroke} className="chart-end" />

          {points.map((p, i) =>
            xLabelAt.has(i) ? (
              <text
                key={p.x + i}
                x={toXY(i, p.y)[0]}
                y={H - 7}
                textAnchor={i === 0 ? "start" : i === points.length - 1 ? "end" : "middle"}
                className="chart-tick"
              >
                {fmtClock(p.x)}
              </text>
            ) : null,
          )}
        </svg>
        <div
          className={`chart-tip${hover !== null ? " on" : ""}`}
          style={
            hover !== null
              ? { left: `${(probe![0] / W) * 100}%`, top: `${(probe![1] / H) * 100}%` }
              : undefined
          }
          aria-hidden="true"
        >
          {hover !== null
            ? `${fmtStamp(points[hover].x)} · ${points[hover].y.toFixed(2)}${unit}`
            : ""}
        </div>
      </div>
      <div className="chart-legend">
        <span>
          min {rawMin.toFixed(2)}
          {unit} · max {rawMax.toFixed(2)}
          {unit} · latest {last.y.toFixed(2)}
          {unit}
        </span>
        {showMarkerLegend &&
          presentSev.map((s) => (
            <span key={s} className="legend-key">
              <span className="legend-swatch" style={{ background: SEV_VAR[s], height: 8, width: 8, borderRadius: "50%" }} />
              {markers.filter((m) => m.severity === s).length} {s}
            </span>
          ))}
      </div>
    </div>
  );
}

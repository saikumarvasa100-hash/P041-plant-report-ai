# P041 Operations Console — design system

## Art direction

A **machine-enamel instrument panel**: the reference is physical plant equipment
— enamel nameplates, oxide-red machinery, petrol instrumentation, engraved
legends on brushed steel — not a dark "AI" dashboard. Dark graphite surfaces,
hairline rules, dense readouts, and colour used only where it carries meaning.

Deliberately avoided, because they are the recognised model reflex for an
"industrial dashboard": neon cyan on navy, glassmorphic blur, gradient-filled
buttons, glow shadows, pill-shaped everything, and a four-equal-card grid.

## Colour tokens

All pairs verified against WCAG AA. Text tokens are ≥4.5:1 on the surface they
sit on; `--line-strong` is 3.16:1 on `--surface` for component edges.
`--line` is a decorative hairline (table rows, chart grid) and is exempt from
the 3:1 non-text requirement.

| token | value | role | contrast |
|---|---|---|---|
| `--canvas` | `#0d0f12` | gutter between panels; never behind text | — |
| `--surface` | `#1c2126` | panel face | — |
| `--surface-2` | `#171b1f` | sidebar, table stripes, insets | — |
| `--surface-3` | `#262c32` | hover | — |
| `--ink` | `#e8ecef` | primary text | 13.65:1 |
| `--ink-2` | `#a3aeb6` | secondary text | 7.17:1 |
| `--ink-3` | `#8a949c` | tertiary text, sparklines | 5.25:1 |
| `--line` | `#262d34` | decorative hairline | — |
| `--line-strong` | `#646f78` | component edges | 3.16:1 |
| `--accent` | `#4fd1c5` | primary accent, active nav | 8.69:1 |
| `--critical` | `#f2554b` | critical severity | 4.77:1 |
| `--warn` | `#e0a030` | high severity, maintenance | 7.14:1 |
| `--ok` | `#3fb97a` | running, nominal | 6.51:1 |
| `--steel` | `#6ba8e0` | medium severity | 6.41:1 |

Each severity also has a `-soft` tint for pill backgrounds; the text on those
tints was checked separately (worst case 4.59:1). `--accent` is a light tone, so
anything filled with it uses dark text (`#06282a`, 8.37:1) — never white, which
would be 1.87:1.

## Typography

- **Barlow Condensed** — page titles, KPI numbers, panel titles. The numerals are
  the thing an operator reads across a room, so they get the display face.
- **Barlow** — body and UI text.
- **JetBrains Mono** — timestamps, telemetry, model/provider metadata, table
  numerics. All numeric cells use `tabular-nums` so columns align.

## Layout archetype

A fixed application shell, not a page:

```
grid-template-columns: 236px 1fr;
grid-template-rows:    70px 1fr;
height: 100dvh;  body { overflow: hidden }
```

The workspace scrolls internally. The body never scrolls, so the viewport is the
product rather than a page containing a dashboard.

Workspace content is a 12-column grid (`.grid-12` + `.col-*`). The overview
keeps an 8/4 production+health split down to 900px because that is what holds
both panels in the first viewport; below it the grid becomes one column.

## Density

24px outer content rhythm, 16px card gaps, 6px panel radius, 4px control radius.
Sidebar 236px. Panels are separated by a 1px border rather than a large tonal
jump, so the console reads as one continuous instrument face.

## Component vocabulary

- **Panel** — the only container. Title in display face, uppercase, tracked.
- **Readout** — label above value, mono, the engraved-legend pattern.
- **KPI** — the number is the largest element; unit, note and backend trend
  delta sit beneath at legend size. A sparkline or severity strip fills the base.
- **Mark** — severity and machine state. Encoded as *shape* (triangle, diamond,
  square, bar, circle, ring) **and** colour, so meaning survives without colour.
- **Drawer** — right-side detail, Escape closes, focus moves in and returns.
- **Severity bar** — share of anomalies by severity, width-encoded with counts
  always shown, never colour alone.

## Motion

One orchestrated page-load reveal. Everything else is a state transition
(hover, drawer open, fold). A critical event's marker pulses slowly (2.6s). All
motion is disabled under `prefers-reduced-motion`.

## Data rules

- Every figure comes from the API. Trends are read from `analytics.trends`;
  nothing is computed in React.
- Machine state comes from each unit's **latest observation**, not from period
  counters — a unit that faulted once in 48 periods is not "FAULT" now.
- Report generation is never automatic. A provider request happens only when the
  user asks for one, and the UI shows a real elapsed timer rather than a staged
  progress animation the backend never emits.
- `numbers_verified: false` is labelled "Validation warning" and described as a
  figure not reproduced verbatim — not as the model altering the analytics.

## Responsive principles

Breakpoints are set where the layout actually breaks, not at device names.

| width | behaviour |
|---|---|
| ≥1241 | full 12-column grid, 5-up KPI strip |
| ≤1240 | 3-up KPI strip, narrow rails widen |
| ≤1024 | sidebar collapses to a 68px rail (accessible names retained) |
| ≤900 | workspace becomes a single column |
| ≤760 | sidebar becomes a wrapping top nav, 3 items per row, 2-up KPIs |
| ≤300 | KPIs become a single column |

Verified with zero page overflow and zero clipped content at 320, 360, 390, 430,
768, 1024, 1200 and 1400px.

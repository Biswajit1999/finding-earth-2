/**
 * The signature element of this interface.
 *
 * This project's argument is about evidence quality, so the credible interval —
 * not the point estimate — is the thing the design repeats. A planet whose ESI
 * is 0.94 +0.01 -0.01 and one whose ESI is 0.94 +0.09 -0.09 are drawn
 * differently everywhere they appear, because they are different claims.
 *
 * The bar is decorative in no sense: its width IS the 16th-to-84th percentile
 * range from the Monte Carlo propagation, on a shared axis, so intervals are
 * directly comparable between rows.
 */

import { num } from "@/lib/format";

export function UncertaintyBar({
  lo,
  mid,
  hi,
  min = 0,
  max = 1,
  width = 120,
  height = 14,
  tone = "var(--color-cyan)",
  label,
  showTicks = false,
}: {
  lo: number | null;
  mid: number | null;
  hi: number | null;
  min?: number;
  max?: number;
  width?: number;
  height?: number;
  tone?: string;
  label?: string;
  showTicks?: boolean;
}) {
  if (mid === null || !Number.isFinite(mid)) {
    return (
      <span
        className="inline-block font-[family-name:var(--font-mono)] text-[11px] text-[var(--color-muted)]"
        style={{ width }}
      >
        no posterior
      </span>
    );
  }

  const span = max - min || 1;
  const clamp = (v: number) => Math.max(0, Math.min(1, (v - min) / span));

  const xMid = clamp(mid) * width;
  const hasInterval =
    lo !== null && hi !== null && Number.isFinite(lo) && Number.isFinite(hi) && hi > lo;
  const xLo = hasInterval ? clamp(lo as number) * width : xMid;
  const xHi = hasInterval ? clamp(hi as number) * width : xMid;

  const cy = height / 2;
  const description = hasInterval
    ? `${label ?? "Value"} ${num(mid, 3)}, 68% credible interval ${num(lo, 3)} to ${num(hi, 3)}`
    : `${label ?? "Value"} ${num(mid, 3)}, no uncertainty published`;

  return (
    <svg
      width={width}
      height={height}
      viewBox={`0 0 ${width} ${height}`}
      role="img"
      aria-label={description}
      className="overflow-visible align-middle"
    >
      {/* axis */}
      <line
        x1={0}
        y1={cy}
        x2={width}
        y2={cy}
        stroke="var(--color-line-strong)"
        strokeWidth={1}
      />
      {showTicks &&
        [0, 0.25, 0.5, 0.75, 1].map((t) => (
          <line
            key={t}
            x1={t * width}
            y1={cy - 2.5}
            x2={t * width}
            y2={cy + 2.5}
            stroke="var(--color-line-strong)"
            strokeWidth={1}
          />
        ))}

      {/* credible interval */}
      {hasInterval && (
        <>
          <line
            x1={xLo}
            y1={cy}
            x2={xHi}
            y2={cy}
            stroke={tone}
            strokeOpacity={0.45}
            strokeWidth={height * 0.42}
            strokeLinecap="butt"
          />
          <line x1={xLo} y1={cy - 4} x2={xLo} y2={cy + 4} stroke={tone} strokeWidth={1.2} />
          <line x1={xHi} y1={cy - 4} x2={xHi} y2={cy + 4} stroke={tone} strokeWidth={1.2} />
        </>
      )}

      {/* median. A hollow marker when no interval exists, so "unquantified"
          is visually distinct from "precisely measured" rather than looking
          like the tightest possible constraint. */}
      {hasInterval ? (
        <circle cx={xMid} cy={cy} r={3.1} fill={tone} stroke="var(--color-void)" strokeWidth={1} />
      ) : (
        <circle
          cx={xMid}
          cy={cy}
          r={3.1}
          fill="none"
          stroke={tone}
          strokeWidth={1.3}
          strokeDasharray="2 1.6"
        />
      )}
    </svg>
  );
}

/**
 * Compact score meter for the four component scores.
 * Uses a filled track plus a numeric readout — colour is never the only signal.
 */
export function ScoreMeter({
  value,
  tone = "var(--color-cyan)",
  width = 84,
  label,
}: {
  value: number | null;
  tone?: string;
  width?: number;
  label: string;
}) {
  const v = value !== null && Number.isFinite(value) ? Math.max(0, Math.min(1, value)) : null;

  return (
    <span className="inline-flex items-center gap-2">
      <span
        role="img"
        aria-label={v === null ? `${label}: not available` : `${label}: ${num(v, 3)} of 1`}
        className="relative inline-block h-[5px] overflow-hidden rounded-full bg-[var(--color-raised)]"
        style={{ width }}
      >
        {v !== null && (
          <span
            className="absolute inset-y-0 left-0 rounded-full"
            style={{ width: `${v * 100}%`, background: tone }}
          />
        )}
      </span>
      <span className="font-[family-name:var(--font-mono)] text-[11px] tabular-nums text-[var(--color-dim)]">
        {v === null ? "—" : num(v, 3)}
      </span>
    </span>
  );
}

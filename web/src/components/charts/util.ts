import type { SeriesInputs } from "@/lib/types";

export const NEUTRAL = ["#2d3748", "#718096", "#a0aec0", "#4a5568"];
export const FLAG_COLOURS: Record<string, string> = {
  neighbour_intensity_fallback_flag: "#dd6b20", gap_interpolated_flag: "#d53f8c", weather_missing: "#805ad5", beam_negative: "#e53e3e", gap_filled_flag: "#c53030",
};
export const ROLE_COL: Record<string, string> = { "SFH-low": "#2b6cb0", "SFH-mid": "#3182ce", "SFH-high": "#90cdf4", "MFH-small": "#2f855a", "MFH-medium": "#48bb78", "MFH-large": "#9ae6b4" };
export const WD = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"];

const tsCache = new WeakMap<SeriesInputs, number[]>();
/** Millisecond UTC timestamps of every hour (start-of-hour index of the bundle). */
export function timestamps(si: SeriesInputs): number[] {
  let t = tsCache.get(si);
  if (!t) {
    const t0 = Date.parse(si.start_utc);
    t = Array.from({ length: si.n }, (_, i) => t0 + i * si.step_s * 1000);
    tsCache.set(si, t);
  }
  return t;
}

export const pairs = (ts: number[], v: (number | null)[]): [number, number | null][] => v.map((x, i) => [ts[i], x]);

/** Consecutive flagged hours as [start, end] index pairs (end inclusive). */
export function runs(flag: number[]): [number, number][] {
  const out: [number, number][] = [];
  let s = -1;
  for (let i = 0; i <= flag.length; i++) {
    if (i < flag.length && flag[i]) { if (s < 0) s = i; } else if (s >= 0) { out.push([s, i - 1]); s = -1; }
  }
  return out;
}
export const count = (a: number[]) => a.reduce((n, v) => n + (v ? 1 : 0), 0);
export const idxWhere = (a: number[]) => a.flatMap((v, i) => (v ? [i] : []));

export const fmt = (v: number | null | undefined, d = 2) => (v == null || Number.isNaN(v) ? "–" : (+v).toFixed(d));

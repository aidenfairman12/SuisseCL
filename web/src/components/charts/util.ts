import { useNames } from "@/lib/names";
import type { SeriesInputs, StoryData } from "@/lib/types";

export const NEUTRAL = ["#2d3748", "#718096", "#a0aec0", "#4a5568"];
export const FLAG_COLOURS: Record<string, string> = {
  neighbour_intensity_fallback_flag: "#dd6b20", gap_interpolated_flag: "#d53f8c", weather_missing: "#805ad5", beam_negative: "#e53e3e", gap_filled_flag: "#c53030",
};
export const ROLE_COL: Record<string, string> = { "SFH-low": "#2b6cb0", "SFH-mid": "#3182ce", "SFH-high": "#90cdf4", "MFH-small": "#2f855a", "MFH-medium": "#48bb78", "MFH-large": "#9ae6b4" };
/** Plain display name of a building role ("Single-family house (low use)"): the `_buildings` names of ui_map.yaml, via story.json. */
export function useBuildingLabel(): (role: string) => string {
  return useNames().building;
}
/** Secondary tooltip text: the role code as named in the data, plus any technical extras (η, supply temperature, ...). */
export const roleTip = (role: string, ...extras: (string | undefined)[]) => [role, ...extras].filter(Boolean).join(" · ");
/** Plain name of a kind of building ("SFH" -> "Single-family houses"), from ui_map `_building_groups`. */
export const buildingGroupLabel = (story: StoryData | null | undefined, group: string) => story?.building_groups[group] ?? group;

/** Axis-tooltip formatter. `series` maps a series name to secondary text shown under its line; `head` maps the axis label to secondary text under the header. */
export function axisTip(opts: { series?: Record<string, string>; head?: Record<string, string> } = {}) {
  type P = { seriesName?: string; marker?: string; value?: unknown; axisValueLabel?: string; name?: string };
  return (raw: unknown) => {
    const ps = (Array.isArray(raw) ? raw : [raw]) as P[];
    const head = ps[0]?.axisValueLabel ?? ps[0]?.name ?? "";
    const sub = (t?: string) => (t ? `<div style="opacity:.65;font-size:11px">${t}</div>` : "");
    const lines = ps.map((q) => {
      const v = Array.isArray(q.value) ? q.value[q.value.length - 1] : q.value;
      return `<div>${q.marker ?? ""} ${q.seriesName}: <b>${v ?? "–"}</b>${sub(opts.series?.[q.seriesName ?? ""])}</div>`;
    });
    return `<div><b>${head}</b>${sub(opts.head?.[head])}</div>${lines.join("")}`;
  };
}

/** The rank-based wording of the modeled carbon intensity of one hour ("Cleaner than 80 % of hours in 2023"). Templates come from story.json. */
export function carbonRelative(si: SeriesInputs, story: StoryData | null | undefined, i: number): { line: string; sub: string } | null {
  const t = story?.carbon_relative;
  if (!t) return null;
  const r = si.carbon_rank.values[i];
  const fill = (s: string, pct: number) => s.replace("{pct}", String(pct)).replace("{year}", String(si.carbon_rank.year));
  const sub = fill(t.sub, 0);
  if (r == null) return { line: t.missing, sub };
  const [lo, hi] = t.typical_band_pct;
  if (r >= lo && r <= hi) return { line: fill(t.typical, r), sub };
  return { line: r < lo ? fill(t.cleaner, 100 - r) : fill(t.dirtier, r), sub };
}

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

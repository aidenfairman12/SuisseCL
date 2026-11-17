import type { Json } from "@/lib/types";

/** Flatten a QC/validation JSON object to [path, value] rows for display (values exactly as stored). */
export function flatten(obj: Json | undefined, prefix = "", out: [string, Json][] = [], depth = 0): [string, Json][] {
  if (obj === undefined) return out;
  if (obj !== null && typeof obj === "object" && !Array.isArray(obj) && depth < 6) {
    for (const [k, v] of Object.entries(obj)) flatten(v, prefix ? `${prefix} › ${k}` : k, out, depth + 1);
  } else if (Array.isArray(obj)) {
    if (obj.every((x) => x === null || typeof x !== "object")) out.push([prefix, obj.map((x) => (typeof x === "number" ? +x.toPrecision(6) : x)).join(", ")]);
    else obj.forEach((x, i) => flatten(x, `${prefix} › ${i}`, out, depth + 1));
  } else out.push([prefix, obj]);
  return out;
}

export function fmtJson(v: Json): string {
  if (v === null) return "n/a";
  if (typeof v === "number") return Number.isInteger(v) ? String(v) : String(+v.toPrecision(6));
  return String(v);
}

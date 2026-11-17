"use client";
// Plain display names (from story.json / the bundle). Registry IDs stay available as secondary text.
import { useMemo } from "react";
import { useBundle } from "./bundle";
import type { NodeT } from "./types";

export const nodeName = (n: NodeT | undefined, fallback = "") => (n ? (n.display_name || n.title) : fallback);

export function useNames() {
  const { story, nodes } = useBundle();
  return useMemo(() => ({
    /** Controller as named in the results file, e.g. "Night-charging rule". */
    ctrl: (c: string) => story?.controllers[c]?.display_name ?? c,
    ctrlShort: (c: string) => story?.controllers[c]?.short_name ?? c,
    ctrlNote: (c: string) => story?.controllers[c]?.note,
    /** The registry controller ID behind a results controller, e.g. "ALG-003". */
    ctrlId: (c: string) => story?.controllers[c]?.node ?? c.split("_")[0],
    building: (role: string) => story?.buildings[role] ?? role,
    kpi: (col: string) => nodeName(nodes[`kpi:${col}`], col),
    node: (id: string) => nodeName(nodes[id], id),
  }), [story, nodes]);
}

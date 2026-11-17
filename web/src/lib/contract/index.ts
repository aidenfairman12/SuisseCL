"use client";
// Typed access to the contract files in /bundle/sim/. Owned by the simulation workstream.
// loadBundleFile and useBundleFile (lib/bundle.tsx) are reused; their names may contain a folder ("sim/manifest").
import { useBundleFile } from "@/lib/bundle";
import type { BuildingsFile, ComparisonsFile, ComponentsFile, ConditionsFile, Manifest, RunFile } from "./types";

export * from "./types";
export * from "./units";

const useSim = <T>(file: string | null) => useBundleFile<T>(file ? `sim/${file}` : null);

export const useManifest = () => useSim<Manifest>("manifest");
export const useBuildings = () => useSim<BuildingsFile>("buildings");
export const useComponents = () => useSim<ComponentsFile>("components");
export const useConditions = () => useSim<ConditionsFile>("conditions");
export const useComparisons = () => useSim<ComparisonsFile>("comparisons");
/** One run = one controller in one scenario (ids from manifest.controllers / manifest.scenarios). Pass null until chosen. */
export const useRun = (scenario: string | null, controller: string | null) => useSim<RunFile>(scenario && controller ? `runs/${scenario}/${controller}` : null);

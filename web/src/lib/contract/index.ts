"use client";
// Typed access to the contract files in /bundle/sim/. Owned by the simulation workstream.
// loadBundleFile and useBundleFile (lib/bundle.tsx) are reused; their names may contain a folder ("sim/manifest").
import { useBundleFile } from "@/lib/bundle";
import type { BuildingsFile, ComparisonsFile, ComponentsFile, ConditionsFile, Manifest, RunFile } from "./types";

export * from "./types";
export * from "./units";

/** "sample" = /bundle/sim/ (48 hours, committed for development); "full" = /bundle/sim_full/ (the whole year). Same files, same schema: read the length from scope.n_steps. */
export type SimVariant = "sample" | "full";
const simDir = (variant: SimVariant) => (variant === "full" ? "sim_full" : "sim");
const useSim = <T>(file: string | null, variant: SimVariant = "sample") => useBundleFile<T>(file ? `${simDir(variant)}/${file}` : null);

export const useManifest = (variant: SimVariant = "sample") => useSim<Manifest>("manifest", variant);
export const useBuildings = (variant: SimVariant = "sample") => useSim<BuildingsFile>("buildings", variant);
export const useComponents = (variant: SimVariant = "sample") => useSim<ComponentsFile>("components", variant);
export const useConditions = (variant: SimVariant = "sample") => useSim<ConditionsFile>("conditions", variant);
/** Comparisons over the file's `scope`: the sample window (comparisons) or the whole simulated year (comparisons_year). Check `scope.kind` before labelling. */
export const useComparisons = (variant: SimVariant = "sample") => useSim<ComparisonsFile>("comparisons", variant);
export const useComparisonsYear = (variant: SimVariant = "sample") => useSim<ComparisonsFile>("comparisons_year", variant);
/** One run = one controller in one scenario (ids from manifest.controllers / manifest.scenarios). Pass null until chosen. */
export const useRun = (scenario: string | null, controller: string | null, variant: SimVariant = "sample") =>
  useSim<RunFile>(scenario && controller ? `runs/${scenario}/${controller}` : null, variant);

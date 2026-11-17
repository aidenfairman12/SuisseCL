"use client";
// Loads bundle JSON files once and shares them. The UI holds no facts of its own: everything shown comes from here.
import { createContext, useContext, useEffect, useState } from "react";
import type { Meta, NodeT, Provenance } from "./types";

const cache = new Map<string, Promise<unknown>>();

export function loadBundleFile<T>(name: string): Promise<T> {
  let p = cache.get(name);
  if (!p) {
    p = fetch(`/bundle/${name}.json`).then((r) => {
      if (!r.ok) throw new Error(`bundle file ${name}.json: HTTP ${r.status}`);
      return r.json();
    });
    cache.set(name, p);
    p.catch(() => cache.delete(name));
  }
  return p as Promise<T>;
}

/** Load any bundle file (e.g. "series_inputs", "figures", "results", "trace_<controller>"). */
export function useBundleFile<T>(name: string | null): { data: T | null; error: string | null } {
  const [state, setState] = useState<{ name: string | null; data: T | null; error: string | null }>({ name: null, data: null, error: null });
  useEffect(() => {
    if (!name) return;
    let live = true;
    loadBundleFile<T>(name).then(
      (d) => live && setState({ name, data: d, error: null }),
      (e: Error) => live && setState({ name, data: null, error: e.message }),
    );
    return () => {
      live = false;
    };
  }, [name]);
  if (state.name !== name) return { data: null, error: null };
  return { data: state.data, error: state.error };
}

type Ctx = { meta: Meta | null; prov: Provenance | null; nodes: Record<string, NodeT>; colours: Record<string, string>; error: string | null };
const BundleCtx = createContext<Ctx>({ meta: null, prov: null, nodes: {}, colours: {}, error: null });

export function BundleProvider({ children }: { children: React.ReactNode }) {
  const [meta, setMeta] = useState<Meta | null>(null);
  const [prov, setProv] = useState<Provenance | null>(null);
  const [error, setError] = useState<string | null>(null);
  useEffect(() => {
    loadBundleFile<Meta>("meta").then(setMeta, (e: Error) => setError(e.message));
    loadBundleFile<Provenance>("provenance").then(setProv, (e: Error) => setError(e.message));
  }, []);
  const value: Ctx = {
    meta,
    prov,
    nodes: prov?.nodes ?? {},
    colours: prov?.settings.classification_colours ?? {},
    error,
  };
  return <BundleCtx.Provider value={value}>{children}</BundleCtx.Provider>;
}

export const useBundle = () => useContext(BundleCtx);

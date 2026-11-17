"use client";
import { useBundle } from "@/lib/bundle";

/** Page title plus the one question the page answers (from story.json, `_pages` in ui_map.yaml). */
export function PageHeader({ title, page }: { title: string; page: string }) {
  const { story } = useBundle();
  return (
    <div className="mb-6 max-w-3xl">
      <h1 className="text-2xl font-semibold tracking-tight">{title}</h1>
      <p className="mt-1 text-muted-foreground">{story?.pages[page] ?? " "}</p>
    </div>
  );
}

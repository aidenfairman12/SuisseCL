"use client";
// Audit-card deep links: ?node=ID on any page. Uses the router so browser back/forward walk through cards.
import { usePathname, useRouter, useSearchParams } from "next/navigation";
import { useCallback } from "react";

export function useNodeParam() {
  const params = useSearchParams();
  const pathname = usePathname();
  const router = useRouter();
  const id = params.get("node");
  const open = useCallback(
    (next: string) => router.push(`${pathname}?node=${encodeURIComponent(next)}`, { scroll: false }),
    [pathname, router],
  );
  const close = useCallback(() => router.push(pathname, { scroll: false }), [pathname, router]);
  return { id, open, close, pathname };
}

export function nodeHref(pathname: string, id: string) {
  return `${pathname}?node=${encodeURIComponent(id)}`;
}

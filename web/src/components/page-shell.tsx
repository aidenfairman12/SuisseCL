"use client";
export function PageHeader({ title, lead }: { title: string; lead: string }) {
  return (
    <div className="mb-6 max-w-3xl">
      <h1 className="text-2xl font-semibold tracking-tight">{title}</h1>
      <p className="mt-1 text-muted-foreground">{lead}</p>
    </div>
  );
}

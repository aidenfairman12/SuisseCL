// One palette for the whole site, matching the district view: zinc neutrals, blue = electricity from the grid,
// orange = heat-pump heat (lighter orange = hot water). Every chart takes its colours from here so a quantity
// keeps the same colour on every page.
export const PALETTE = {
  ink: "#18181b",
  text: "#3f3f46",
  muted: "#71717a",
  soft: "#a1a1aa",
  faint: "#d4d4d8",
  hair: "#e4e4e7",
  wash: "#f4f4f5",

  grid: "#2563eb",
  gridMid: "#3b82f6",
  gridSoft: "#93c5fd",
  heat: "#ea580c",
  heatDeep: "#c2410c",
  water: "#fb923c",
  household: "#a1a1aa",
  solar: "#ca8a04",
  cool: "#0891b2",
  battery: "#0d9488",
  batterySoft: "#5eead4",
  export: "#7c3aed",
  alert: "#dc2626",
  highlight: "#f59e0b",
} as const;

/** Default categorical order for charts that do not set their own colours. */
export const CATEGORICAL = [PALETTE.grid, PALETTE.heat, PALETTE.battery, PALETTE.solar, PALETTE.export, PALETTE.cool, PALETTE.muted, PALETTE.gridSoft, PALETTE.water];

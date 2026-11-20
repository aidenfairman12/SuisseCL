// Navigation structure shared by the header menu and the story page's deep-dive links.
export type NavItem = { href: string; label: string; hint: string };
export const DEEP_DIVE: { group: string; items: NavItem[] }[] = [
  { group: "Explore", items: [
    { href: "/district/", label: "District", hint: "inspect buildings and timestep flows" },
    { href: "/explorer/", label: "Explorer", hint: "pick a climate, cooling level and controller" },
    { href: "/houses/", label: "Houses", hint: "what cooling adds per building and what reaches the grid" },
    { href: "/climate/", label: "Climate", hint: "warmer weather and a heat-wave week" },
    { href: "/cooling/", label: "Cooling", hint: "warming and cooling levels across the district" },
    { href: "/overview/", label: "Overview", hint: "system scope and energy flows" },
  ] },
  { group: "Methods", items: [
    { href: "/methods/", label: "Data & methods", hint: "sources, licences, pipeline and how it was built" },
    { href: "/scenarios/", label: "Scenarios", hint: "solar, battery, building model and price assumptions" },
    { href: "/controllers/", label: "Controllers", hint: "ideal saving against real controllers" },
    { href: "/results/", label: "Results", hint: "annual controller comparison" },
    { href: "/model/", label: "Model", hint: "devices, assumptions and control" },
    { href: "/inputs/", label: "Inputs", hint: "weather, price, carbon and demand" },
  ] },
  { group: "Audit", items: [
    { href: "/audit/", label: "Audit", hint: "registry, validation and known limitations" },
    { href: "/glossary/", label: "Glossary", hint: "terms and definitions" },
  ] },
];

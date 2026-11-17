// Energy vs power. Series values are ENERGY PER STEP (kWh). Mean power over the step = kWh / (step_seconds / 3600).
// At hourly steps kWh and kW are numerically equal; at the 15-minute steps of Phase B they differ by 4. Always convert.
export const meanKw = (kwhPerStep: number, stepSeconds: number) => kwhPerStep / (stepSeconds / 3600);
export const meanKwSeries = (kwh: number[], stepSeconds: number) => kwh.map((v) => meanKw(v, stepSeconds));

/** A tank fill level of 0 vs "no tank": `soc === null` (whole series null) means the building has no such tank. */
export const hasTank = (soc: number[] | null): soc is number[] => soc !== null;

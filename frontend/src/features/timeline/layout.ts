/** Pure layout helpers for the timeline (architecture 8): kept apart from React so they are testable. */

export function toYear(date: string): number {
  const start = Date.UTC(Number(date.slice(0, 4)), 0, 1);
  const at = new Date(`${date}T00:00:00Z`).getTime();
  return Number(date.slice(0, 4)) + (at - start) / (365.25 * 86400000);
}

/** Semantic zoom (scope 7.2): every event has a dot; the zoom factor decides which levels also get a title. */
export function titledImportance(zoom: number): Set<string> {
  if (zoom >= 3) return new Set(["major", "notable", "minor"]);
  if (zoom >= 1.5) return new Set(["major", "notable"]);
  return new Set(["major"]);
}

/** Puts overlapping bands into separate lanes (phases may overlap, scope 3.1). */
export function assignLanes<T extends { start: number; end: number }>(
  bands: T[],
): (T & { lane: number })[] {
  const laneEnds: number[] = [];
  return [...bands]
    .sort((a, b) => a.start - b.start)
    .map((band) => {
      let lane = laneEnds.findIndex((end) => end <= band.start);
      if (lane === -1) lane = laneEnds.length;
      laneEnds[lane] = band.end;
      return { ...band, lane };
    });
}

/** Greedy label rows: a label gets the first row where it clears the previous one. -1 = no room. */
export function assignLabelRows(
  items: { x: number; width: number }[],
  rows: number,
  gap = 8,
): number[] {
  const rightEdge: number[] = Array(rows).fill(-Infinity);
  return items.map(({ x, width }) => {
    const left = x - width / 2;
    const row = rightEdge.findIndex((edge) => edge + gap <= left);
    if (row === -1) return -1;
    rightEdge[row] = x + width / 2;
    return row;
  });
}

const GRID_STEPS = [1, 5, 10, 20, 50];
const MIN_GRID_GAP_PX = 60;

/** Adaptive grid: the smallest step (years) whose lines stay at least ~60px apart. */
export function pickGridStep(pxPerYear: number): number {
  return GRID_STEPS.find((step) => step * pxPerYear >= MIN_GRID_GAP_PX) ?? GRID_STEPS.at(-1)!;
}

/** Multiples of `step` inside [from, to]. */
export function gridTicks(from: number, to: number, step: number): number[] {
  const ticks: number[] = [];
  for (let year = Math.ceil(from / step) * step; year <= to; year += step) ticks.push(year);
  return ticks;
}

export const MAX_ZOOM = 40;

/** The zoom transform (in base-range pixels) that shows the year span [from, to]. */
export function viewTransform(
  full: [number, number],
  width: number,
  from: number,
  to: number,
): { k: number; x: number } {
  const fullSpan = full[1] - full[0];
  const span = Math.min(fullSpan, Math.max(fullSpan / MAX_ZOOM, to - from));
  const start = Math.min(full[1] - span, Math.max(full[0], from));
  const k = fullSpan / span;
  return { k, x: -((start - full[0]) / fullSpan) * width * k };
}

/** Visible span of the current transform as fractions (0..1) of the full period. */
export function visibleFractions(k: number, x: number, width: number): [number, number] {
  const start = -x / k / width;
  return [start, start + 1 / k];
}

/** One stable color per phase, so a phase looks the same on the timeline and the scrubber. */
export const PHASE_COLORS = ["#a0522d", "#6b705c", "#7a4a6d", "#9b2c2c", "#2f5d62"];
export const phaseColor = (index: number): string => PHASE_COLORS[index % PHASE_COLORS.length];

/** Left edge of a popup centered on a dot but kept inside the chart, plus where its arrow points. */
export function popupPosition(dotX: number, chartWidth: number, popupWidth: number, margin = 4) {
  const left = Math.max(margin, Math.min(dotX - popupWidth / 2, chartWidth - popupWidth - margin));
  return { left, arrow: dotX - left };
}

export const MIN_LANE_H = 72;
export const AXIS_H = 22;

/** Height of one track lane: the chart height shared out evenly, but never below a readable minimum. */
export function laneHeight(chartHeight: number, laneCount: number): number {
  return Math.max(MIN_LANE_H, Math.floor((chartHeight - AXIS_H) / Math.max(1, laneCount)));
}

/** The year span to zoom to when a lane is focused (scope 7.2): the lane's phase band if it has
 * one, otherwise its events, widened a little so the edge dots are not cut off. */
export function focusSpan(
  phase: { start: number; end: number } | null,
  eventYears: number[],
  pad = 2,
): [number, number] | null {
  if (phase) return [phase.start - pad, phase.end + pad];
  if (eventYears.length === 0) return null;
  return [Math.min(...eventYears) - pad, Math.max(...eventYears) + pad];
}

/** A pop-up sits above its dot unless there is too little room, then below it. */
export function popupSide(dotY: number, needed = 200): "above" | "below" {
  return dotY >= needed ? "above" : "below";
}

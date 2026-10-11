/** Pure layout helpers for the timeline (architecture 8): kept apart from React so they are testable. */

export function toYear(date: string): number {
  const start = Date.UTC(Number(date.slice(0, 4)), 0, 1);
  const at = new Date(`${date}T00:00:00Z`).getTime();
  return Number(date.slice(0, 4)) + (at - start) / (365.25 * 86400000);
}

/** Semantic zoom: the zoom factor decides the least important level that is shown. */
export function visibleImportance(zoom: number): Set<string> {
  if (zoom >= 6) return new Set(["major", "notable", "minor"]);
  if (zoom >= 2.5) return new Set(["major", "notable"]);
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

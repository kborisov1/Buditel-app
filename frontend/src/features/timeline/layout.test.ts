import { expect, test } from "vitest";
import { assignLabelRows, assignLanes, toYear, visibleImportance } from "./layout";

test("toYear places a date inside its year", () => {
  expect(toYear("1762-01-01")).toBe(1762);
  expect(toYear("1762-07-02")).toBeCloseTo(1762.5, 1);
});

test("zooming in reveals less important events", () => {
  expect([...visibleImportance(1)]).toEqual(["major"]);
  expect(visibleImportance(3).has("notable")).toBe(true);
  expect(visibleImportance(3).has("minor")).toBe(false);
  expect(visibleImportance(10).has("minor")).toBe(true);
});

test("overlapping phases get separate lanes, others share one", () => {
  const lanes = assignLanes([
    { start: 1820, end: 1856 },
    { start: 1840, end: 1870 },
    { start: 1860, end: 1876 },
  ]);
  expect(lanes.map((l) => l.lane)).toEqual([0, 1, 0]);
});

test("labels that collide move down a row, then are dropped", () => {
  const rows = assignLabelRows(
    [
      { x: 100, width: 80 },
      { x: 120, width: 80 },
      { x: 130, width: 80 },
      { x: 140, width: 80 },
    ],
    3,
  );
  expect(rows).toEqual([0, 1, 2, -1]);
});

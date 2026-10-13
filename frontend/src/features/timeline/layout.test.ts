import { expect, test } from "vitest";
import {
  assignLabelRows,
  assignLanes,
  gridTicks,
  pickGridStep,
  popupPosition,
  toYear,
  viewTransform,
  visibleFractions,
  titledImportance,
} from "./layout";

test("toYear places a date inside its year", () => {
  expect(toYear("1762-01-01")).toBe(1762);
  expect(toYear("1762-07-02")).toBeCloseTo(1762.5, 1);
});

test("zooming in adds titles for less important events", () => {
  expect([...titledImportance(1)]).toEqual(["major"]);
  expect(titledImportance(2).has("notable")).toBe(true);
  expect(titledImportance(2).has("minor")).toBe(false);
  expect(titledImportance(4).has("minor")).toBe(true);
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

test("grid step widens when zoomed out and narrows when zoomed in", () => {
  expect(pickGridStep(10)).toBe(10);
  expect(pickGridStep(14)).toBe(5);
  expect(pickGridStep(70)).toBe(1);
  expect(pickGridStep(0.5)).toBe(50);
  expect(gridTicks(1762, 1800, 10)).toEqual([1770, 1780, 1790, 1800]);
});

test("viewTransform and visibleFractions round-trip and clamp to the period", () => {
  const { k, x } = viewTransform([1750, 1890], 1000, 1800, 1840);
  expect(k).toBeCloseTo(140 / 40);
  const [a, b] = visibleFractions(k, x, 1000);
  expect(1750 + a * 140).toBeCloseTo(1800);
  expect(1750 + b * 140).toBeCloseTo(1840);
  const edge = viewTransform([1750, 1890], 1000, 1880, 1920);
  expect(visibleFractions(edge.k, edge.x, 1000)[1]).toBeCloseTo(1);
});

test("a popup is centered on its dot but stays inside the chart", () => {
  expect(popupPosition(500, 1000, 288)).toEqual({ left: 356, arrow: 144 });
  expect(popupPosition(10, 1000, 288)).toEqual({ left: 4, arrow: 6 });
  expect(popupPosition(990, 1000, 288)).toEqual({ left: 708, arrow: 282 });
});

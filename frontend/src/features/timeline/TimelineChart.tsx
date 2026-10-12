import { scaleLinear, select, zoom, zoomIdentity, type ZoomBehavior } from "d3";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { useTranslation } from "react-i18next";
import type { Timeline } from "../../api/client";
import {
  assignLabelRows,
  assignLanes,
  gridTicks,
  MAX_ZOOM,
  phaseColor,
  pickGridStep,
  toYear,
  viewTransform,
  visibleFractions,
  titledImportance,
} from "./layout";
import TimelineScrubber from "./TimelineScrubber";

const LANE_H = 46;
const BANDS_TOP = 12;
const CHAR_W = 7;
const ROW_H = 20;
const PAD_YEARS = 8; // room so labels at the period edges are not clipped

interface Props {
  timeline: Timeline;
  selected: string | null;
  onSelect: (slug: string) => void;
}

/** Fills its parent. D3 supplies the scales and zoom; React renders the SVG (architecture 8). */
export default function TimelineChart({ timeline, selected, onSelect }: Props) {
  const { t } = useTranslation();
  const areaRef = useRef<HTMLDivElement>(null);
  const svgRef = useRef<SVGSVGElement>(null);
  const zoomRef = useRef<ZoomBehavior<SVGSVGElement, unknown> | null>(null);
  const [size, setSize] = useState({ w: 0, h: 0 });
  const [view, setView] = useState({ k: 1, x: 0 });
  // The view as fractions of the full period survives a resize, unlike pixel offsets.
  const fractions = useRef<[number, number]>([0, 1]);

  const full = useMemo<[number, number]>(
    () => [toYear(timeline.start) - PAD_YEARS, toYear(timeline.end) + 1 + PAD_YEARS],
    [timeline.start, timeline.end],
  );
  const { w, h } = size;
  const base = useMemo(() => scaleLinear().domain(full).range([0, w]), [full, w]);
  const x = zoomIdentity.translate(view.x, 0).scale(view.k).rescaleX(base);

  useEffect(() => {
    const el = areaRef.current;
    if (!el) return;
    const observer = new ResizeObserver(([entry]) =>
      setSize({ w: Math.floor(entry.contentRect.width), h: Math.floor(entry.contentRect.height) }),
    );
    observer.observe(el);
    return () => observer.disconnect();
  }, []);

  useEffect(() => {
    const svg = svgRef.current;
    if (!svg || w === 0) return;
    const behavior = zoom<SVGSVGElement, unknown>()
      .scaleExtent([1, MAX_ZOOM])
      .translateExtent([[0, 0], [w, 1]])
      .extent([[0, 0], [w, 1]])
      .on("zoom", (event) => {
        const { k, x: tx } = event.transform;
        fractions.current = visibleFractions(k, tx, w);
        setView({ k, x: tx });
      });
    zoomRef.current = behavior;
    const selection = select(svg);
    selection.call(behavior);
    const [from, to] = fractions.current;
    const span = full[1] - full[0];
    const next = viewTransform(full, w, full[0] + from * span, full[0] + to * span);
    selection.call(behavior.transform, zoomIdentity.translate(next.x, 0).scale(next.k));
    return () => void selection.on(".zoom", null);
  }, [w, full]);

  /** Shows the year span [from, to]; used by the scrubber. */
  const showSpan = useCallback(
    (from: number, to: number) => {
      const svg = svgRef.current;
      if (!svg || !zoomRef.current) return;
      const next = viewTransform(full, w, from, to);
      select(svg).call(zoomRef.current.transform, zoomIdentity.translate(next.x, 0).scale(next.k));
    },
    [full, w],
  );

  const zoomBy = (factor: number) => {
    if (svgRef.current && zoomRef.current) select(svgRef.current).call(zoomRef.current.scaleBy, factor);
  };

  const bands = useMemo(
    () =>
      assignLanes(
        timeline.phases.map((p, index) => ({ ...p, index, start: toYear(p.start_date), end: toYear(p.end_date) })),
      ),
    [timeline.phases],
  );
  const laneCount = Math.max(1, ...bands.map((b) => b.lane + 1));
  const axisY = Math.round(h * 0.68);
  const labelRows = Math.max(1, Math.min(8, Math.floor((axisY - BANDS_TOP - laneCount * LANE_H - 24) / ROW_H)));

  const [from, to] = [x.invert(0), x.invert(w)];
  const step = pickGridStep(w / Math.max(to - from, 0.001));
  const grid = gridTicks(from, to, step);

  const titled = titledImportance(view.k);
  const events = timeline.events
    .map((e) => ({ event: e, px: x(toYear(e.event_date)), titled: titled.has(e.importance) || e.slug === selected }))
    .filter(({ px }) => px >= -20 && px <= w + 20);
  // Only titled events compete for label rows; the others stay plain dots.
  const titledEvents = events.filter((e) => e.titled);
  const titledRows = assignLabelRows(
    titledEvents.map(({ event, px }) => ({ x: px, width: event.title.length * CHAR_W })),
    labelRows,
  );
  const rows = events.map((e) => (e.titled ? titledRows[titledEvents.indexOf(e)] : -1));

  return (
    <div className="flex h-full min-h-0 flex-col">
      <div className="mb-2 flex gap-2">
        <button className="rounded border border-mocha px-3" onClick={() => zoomBy(1.6)}>
          {t("timeline.zoomIn")}
        </button>
        <button className="rounded border border-mocha px-3" onClick={() => zoomBy(1 / 1.6)}>
          {t("timeline.zoomOut")}
        </button>
        <span className="self-center text-sm">{t("timeline.zoomHint")}</span>
      </div>
      <div ref={areaRef} className="min-h-0 max-h-[640px] flex-1 overflow-hidden rounded border border-cappuccino bg-white/30">
        <svg
          ref={svgRef}
          width={w}
          height={h}
          className="block touch-none select-none"
          role="group"
          aria-label={t("timeline.title")}
        >
          {w > 0 && (
            <>
              {grid.map((year) => (
                <g key={year} transform={`translate(${x(year)},0)`}>
                  <line y1={0} y2={h} stroke="#c8a57a" strokeDasharray="3 6" />
                  <text y={h - 8} x={4} fontSize={11} fill="#8a6a4a">
                    {year}
                  </text>
                </g>
              ))}
              {bands.map((b) => {
                const left = Math.max(x(b.start), 0);
                const right = Math.min(x(b.end), w);
                if (right <= left) return null;
                const y = BANDS_TOP + b.lane * LANE_H;
                const color = phaseColor(b.index);
                const clip = `phase-clip-${b.id}`;
                return (
                  <g key={b.id}>
                    {/* A faint wash down the chart shows where the phase lies under the events. */}
                    <rect x={left} y={y} width={right - left} height={h - y} fill={color} opacity={0.06} />
                    <clipPath id={clip}>
                      <rect x={left} y={y} width={right - left} height={LANE_H - 6} />
                    </clipPath>
                    <rect x={left} y={y} width={right - left} height={LANE_H - 6} rx={6} fill={color} />
                    <g clipPath={`url(#${clip})`} fill="#f4ead5">
                      <text x={left + 12} y={y + 18} fontSize={14} fontWeight={700} fontFamily="'Source Serif 4', serif">
                        {b.name}
                      </text>
                      <text x={left + 12} y={y + 33} fontSize={11} opacity={0.85}>
                        {`${b.start_date.slice(0, 4)}–${b.end_date.slice(0, 4)}`}
                      </text>
                    </g>
                  </g>
                );
              })}
              <line x1={0} x2={w} y1={axisY} y2={axisY} stroke="#4a3326" strokeWidth={1.5} />
              {events.map(({ event, px }, i) => {
                const row = rows[i];
                const active = event.slug === selected;
                const half = (event.title.length * CHAR_W) / 2;
                const anchor = px - half < 4 ? "start" : px + half > w - 4 ? "end" : "middle";
                return (
                  <g
                    key={event.id}
                    transform={`translate(${px},${axisY})`}
                    role="button"
                    tabIndex={0}
                    aria-label={event.title}
                    aria-pressed={active}
                    className="cursor-pointer outline-none focus-visible:[&>circle]:stroke-[3]"
                    onClick={() => onSelect(event.slug)}
                    onKeyDown={(e) => {
                      if (e.key === "Enter" || e.key === " ") {
                        e.preventDefault();
                        onSelect(event.slug);
                      }
                    }}
                  >
                    <title>{event.title}</title>
                    {row >= 0 && (
                      <>
                        <line y1={-4} y2={-16 - row * ROW_H} stroke="#c8a57a" />
                        <text
                          y={-20 - row * ROW_H}
                          textAnchor={anchor}
                          fontSize={13}
                          fontWeight={event.importance === "major" ? 700 : 400}
                          fill="#4a3326"
                          opacity={event.locked ? 0.55 : 1}
                        >
                          {event.title}
                        </text>
                      </>
                    )}
                    <circle
                      r={event.importance === "major" ? 8 : event.importance === "notable" ? 6 : 4.5}
                      fill={event.locked ? "#f4ead5" : active ? "#2b1d14" : "#4a3326"}
                      stroke="#4a3326"
                      strokeWidth={event.locked ? 1.5 : 1}
                      strokeDasharray={event.locked ? "2 2" : undefined}
                    />
                  </g>
                );
              })}
            </>
          )}
        </svg>
      </div>
      <TimelineScrubber
        full={full}
        events={timeline.events}
        phases={timeline.phases}
        visible={[from, to]}
        onChange={showSpan}
      />
    </div>
  );
}

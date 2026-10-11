import { scaleLinear, select, zoom, zoomIdentity, type ZoomBehavior, type ZoomTransform } from "d3";
import { useEffect, useMemo, useRef, useState } from "react";
import { useTranslation } from "react-i18next";
import type { Timeline } from "../../api/client";
import { assignLabelRows, assignLanes, toYear, visibleImportance } from "./layout";

const WIDTH = 1000;
const LANE_H = 22;
const AXIS_Y = 200;
const LABEL_ROWS = 3;
const CHAR_W = 7;
const PAD_YEARS = 8; // room so labels at the period edges are not clipped
const BAND_COLORS = ["#c8a57a", "#a9855a", "#8a6a4a", "#d9bf98", "#6f5340"];

interface Props {
  timeline: Timeline;
  selected: string | null;
  onSelect: (slug: string) => void;
}

/** D3 supplies the scales and zoom; React renders the SVG (architecture 8). */
export default function TimelineChart({ timeline, selected, onSelect }: Props) {
  const { t } = useTranslation();
  const svgRef = useRef<SVGSVGElement>(null);
  const zoomRef = useRef<ZoomBehavior<SVGSVGElement, unknown> | null>(null);
  const [transform, setTransform] = useState<ZoomTransform>(zoomIdentity);

  const base = useMemo(
    () => scaleLinear().domain([toYear(timeline.start) - PAD_YEARS, toYear(timeline.end) + 1 + PAD_YEARS]).range([0, WIDTH]),
    [timeline.start, timeline.end],
  );
  const x = transform.rescaleX(base);
  const tickCount = Math.round(WIDTH / 90);
  const tickLabel = x.tickFormat(tickCount, "d");

  useEffect(() => {
    const svg = svgRef.current;
    if (!svg) return;
    const behavior = zoom<SVGSVGElement, unknown>()
      .scaleExtent([1, 40])
      .translateExtent([[0, 0], [WIDTH, 1]])
      .extent([[0, 0], [WIDTH, 1]])
      .on("zoom", (event) => setTransform(event.transform));
    zoomRef.current = behavior;
    select(svg).call(behavior);
    return () => void select(svg).on(".zoom", null);
  }, []);

  const bands = useMemo(
    () =>
      assignLanes(
        timeline.phases.map((p) => ({ ...p, start: toYear(p.start_date), end: toYear(p.end_date) })),
      ),
    [timeline.phases],
  );

  const shown = visibleImportance(transform.k);
  const events = timeline.events
    .filter((e) => shown.has(e.importance) || e.slug === selected)
    .map((e) => ({ event: e, px: x(toYear(e.event_date)) }))
    .filter(({ px }) => px >= -20 && px <= WIDTH + 20);
  const rows = assignLabelRows(
    events.map(({ event, px }) => ({ x: px, width: event.title.length * CHAR_W })),
    LABEL_ROWS,
  );

  const zoomBy = (factor: number) => {
    if (svgRef.current && zoomRef.current) {
      select(svgRef.current).call(zoomRef.current.scaleBy, factor);
    }
  };

  return (
    <div>
      <div className="mb-2 flex gap-2">
        <button className="rounded border border-mocha px-3" onClick={() => zoomBy(1.6)}>
          {t("timeline.zoomIn")}
        </button>
        <button className="rounded border border-mocha px-3" onClick={() => zoomBy(1 / 1.6)}>
          {t("timeline.zoomOut")}
        </button>
        <span className="self-center text-sm">{t("timeline.zoomHint")}</span>
      </div>
      <svg
        ref={svgRef}
        viewBox={`0 0 ${WIDTH} ${AXIS_Y + 40}`}
        className="w-full touch-none select-none rounded border border-cappuccino bg-white/30"
        role="group"
        aria-label={t("timeline.title")}
      >
        <defs>
          <clipPath id="timeline-area">
            <rect x={0} y={0} width={WIDTH} height={AXIS_Y + 40} />
          </clipPath>
        </defs>
        <g clipPath="url(#timeline-area)">
          {bands.map((b, i) => {
            const left = Math.max(x(b.start), 0);
            const right = Math.min(x(b.end), WIDTH);
            if (right <= left) return null;
            return (
              <g key={b.id}>
                <rect
                  x={left}
                  y={8 + b.lane * LANE_H}
                  width={right - left}
                  height={LANE_H - 4}
                  rx={3}
                  fill={BAND_COLORS[i % BAND_COLORS.length]}
                  opacity={0.7}
                />
                <text x={left + 6} y={8 + b.lane * LANE_H + 13} fontSize={11} fill="#2b1d14">
                  {b.name}
                </text>
              </g>
            );
          })}
          <line x1={0} x2={WIDTH} y1={AXIS_Y} y2={AXIS_Y} stroke="#4a3326" />
          {x.ticks(tickCount).map((tick) => (
            <g key={tick} transform={`translate(${x(tick)},${AXIS_Y})`}>
              <line y2={6} stroke="#4a3326" />
              <text y={20} textAnchor="middle" fontSize={11} fill="#4a3326">
                {tickLabel(tick)}
              </text>
            </g>
          ))}
          {events.map(({ event, px }, i) => {
            const row = rows[i];
            const active = event.slug === selected;
            return (
              <g
                key={event.id}
                transform={`translate(${px},${AXIS_Y})`}
                role="button"
                tabIndex={0}
                aria-label={event.title}
                aria-pressed={active}
                className="cursor-pointer outline-none focus-visible:[&>circle]:stroke-2"
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
                    <line y1={-4} y2={-18 - row * 18} stroke="#c8a57a" />
                    <text
                      y={-22 - row * 18}
                      textAnchor="middle"
                      fontSize={12}
                      fontWeight={event.importance === "major" ? 700 : 400}
                      fill="#4a3326"
                      opacity={event.locked ? 0.55 : 1}
                    >
                      {event.title}
                    </text>
                  </>
                )}
                <circle
                  r={event.importance === "major" ? 7 : event.importance === "notable" ? 5.5 : 4}
                  fill={event.locked ? "#f4ead5" : active ? "#2b1d14" : "#4a3326"}
                  stroke="#4a3326"
                  strokeWidth={event.locked ? 1.5 : 1}
                  strokeDasharray={event.locked ? "2 2" : undefined}
                />
              </g>
            );
          })}
        </g>
      </svg>
    </div>
  );
}

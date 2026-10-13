import { scaleLinear, select, zoom, zoomIdentity, type ZoomBehavior } from "d3";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { useTranslation } from "react-i18next";
import type { Timeline, TimelineEvent } from "../../api/client";
import {
  assignLabelRows,
  AXIS_H,
  focusSpan,
  gridTicks,
  laneHeight,
  MAX_ZOOM,
  phaseColor,
  pickGridStep,
  popupPosition,
  popupSide,
  titledImportance,
  toYear,
  viewTransform,
  visibleFractions,
} from "./layout";
import EventPopup, { POPUP_WIDTH } from "./EventPopup";
import TimelineScrubber from "./TimelineScrubber";

const HEADER_H = 26; // room at the top of a lane for its name and focus button
const DOT_FROM_BOTTOM = 24;
const NO_TRACK = 0; // lane for events that belong to no track
const CHAR_W = 7;
const ROW_H = 20;
const PAD_YEARS = 8; // room so labels at the period edges are not clipped

interface Props {
  timeline: Timeline;
  selected: string | null;
  onSelect: (slug: string | null) => void;
  /** The focused lane (scope 7.2): the others fade and the view zooms to it. */
  focus: number | null;
  onFocus: (trackId: number | null) => void;
}

/** Fills its parent. D3 supplies the scales and zoom; React renders the SVG (architecture 8). */
export default function TimelineChart({ timeline, selected, onSelect, focus, onFocus }: Props) {
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

  const phaseIndex = useMemo(() => new Map(timeline.phases.map((p, i) => [p.id, i])), [timeline.phases]);
  const lanes = useMemo(() => {
    const list = timeline.tracks.map((track) => {
      const phase = timeline.phases.find((p) => p.id === track.phase_id) ?? null;
      return { id: track.id, name: track.name, open: track.open, phase };
    });
    // Events that sit in no track still need a place on the chart.
    if (timeline.events.some((e) => e.track_ids.length === 0)) {
      list.push({ id: NO_TRACK, name: t("timeline.otherLane"), open: true, phase: null });
    }
    return list;
  }, [timeline.tracks, timeline.phases, timeline.events, t]);

  const laneH = laneHeight(h, lanes.length);
  const svgH = lanes.length * laneH + AXIS_H;
  const labelRows = Math.max(1, Math.floor((laneH - HEADER_H - DOT_FROM_BOTTOM - 14) / ROW_H));

  const [from, to] = [x.invert(0), x.invert(w)];
  const step = pickGridStep(w / Math.max(to - from, 0.001));
  const grid = gridTicks(from, to, step);

  const titled = titledImportance(view.k);
  const laneDots = lanes.map((lane, index) => {
    const dotY = index * laneH + laneH - DOT_FROM_BOTTOM;
    const dots = timeline.events
      .filter((e) => (e.track_ids.length === 0 ? lane.id === NO_TRACK : e.track_ids.includes(lane.id)))
      .map((e) => ({ event: e, px: x(toYear(e.event_date)) }))
      .filter(({ px }) => px >= -20 && px <= w + 20);
    const dimmed = focus !== null && focus !== lane.id;
    const isTitled = (e: TimelineEvent) => !dimmed && (titled.has(e.importance) || e.slug === selected);
    // Only titled events compete for label rows; the others stay plain dots.
    const withTitle = dots.filter(({ event }) => isTitled(event));
    const rowOf = assignLabelRows(
      // A title near an edge is anchored to it, so collisions use where it is really drawn.
      withTitle.map(({ event, px }) => {
        const width = event.title.length * CHAR_W;
        return { x: Math.min(Math.max(px, width / 2 + 4), w - width / 2 - 4), width };
      }),
      labelRows,
    );
    return {
      lane,
      index,
      dotY,
      dimmed,
      dots: dots.map((d) => ({ ...d, row: isTitled(d.event) ? rowOf[withTitle.indexOf(d)] : -1 })),
    };
  });

  // The popup follows its dot while zooming and hides once the dot leaves the view.
  const popupDot = laneDots
    .flatMap((l) => l.dots.map((d) => ({ ...d, dotY: l.dotY })))
    .find(({ event, px }) => event.slug === selected && px >= 0 && px <= w);
  const popupWidth = Math.min(POPUP_WIDTH, w - 8);

  function toggleFocus(laneId: number) {
    if (focus === laneId) return onFocus(null);
    onFocus(laneId);
  }

  // Focusing zooms to the lane's range; leaving focus shows the whole period again.
  useEffect(() => {
    if (w === 0) return;
    if (focus === null) return showSpan(full[0], full[1]);
    const lane = lanes.find((l) => l.id === focus);
    if (!lane) return;
    const years = timeline.events
      .filter((e) => e.track_ids.includes(lane.id))
      .map((e) => toYear(e.event_date));
    const phase = lane.phase ? { start: toYear(lane.phase.start_date), end: toYear(lane.phase.end_date) } : null;
    const span = focusSpan(phase, years);
    if (span) showSpan(span[0], span[1]);
    // Only a change of focus should move the view, not later pans or data refreshes.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [focus, w]);

  return (
    <div className="flex h-full min-h-0 flex-col">
      <div className="mb-2 flex flex-wrap gap-2">
        <button className="rounded border border-mocha px-3" onClick={() => zoomBy(1.6)}>
          {t("timeline.zoomIn")}
        </button>
        <button className="rounded border border-mocha px-3" onClick={() => zoomBy(1 / 1.6)}>
          {t("timeline.zoomOut")}
        </button>
        <span className="self-center text-sm">{t("timeline.zoomHint")}</span>
      </div>
      <div ref={areaRef} className="relative min-h-0 max-h-[640px] flex-1 overflow-y-auto overflow-x-hidden rounded border border-cappuccino bg-white/30">
        <div className="relative" style={{ height: svgH }}>
        <svg
          ref={svgRef}
          width={w}
          height={svgH}
          className="block touch-none select-none"
          role="group"
          aria-label={t("timeline.title")}
          onClick={() => onSelect(null)}
        >
          {w > 0 && (
            <>
              {grid.map((year) => (
                <g key={year} transform={`translate(${x(year)},0)`}>
                  <line y1={0} y2={svgH} stroke="#c8a57a" strokeDasharray="3 6" />
                  <text y={svgH - 8} x={4} fontSize={11} fill="#8a6a4a">
                    {year}
                  </text>
                </g>
              ))}
              {laneDots.map(({ lane, index, dotY, dimmed, dots }) => {
                const top = index * laneH;
                const color = lane.phase ? phaseColor(phaseIndex.get(lane.phase.id) ?? 0) : "#8a6a4a";
                const left = lane.phase ? Math.max(x(toYear(lane.phase.start_date)), 0) : 0;
                const right = lane.phase ? Math.min(x(toYear(lane.phase.end_date)), w) : 0;
                const clip = `lane-clip-${lane.id}`;
                return (
                  <g key={lane.id} opacity={dimmed ? 0.3 : 1}>
                    <line x1={0} x2={w} y1={top + laneH} y2={top + laneH} stroke="#c8a57a" opacity={0.6} />
                    {lane.phase && right > left && (
                      <>
                        <rect x={left} y={top} width={right - left} height={laneH} fill={color} opacity={0.16} />
                        <rect x={left} y={top} width={right - left} height={3} fill={color} />
                        <clipPath id={clip}>
                          <rect x={left} y={top} width={right - left} height={laneH} />
                        </clipPath>
                        <text
                          clipPath={`url(#${clip})`}
                          x={left + 8}
                          y={top + laneH - 6}
                          fontSize={11}
                          fill={color}
                          fontWeight={600}
                        >
                          {`${lane.phase.name} ${lane.phase.start_date.slice(0, 4)}–${lane.phase.end_date.slice(0, 4)}`}
                        </text>
                      </>
                    )}
                    <line x1={0} x2={w} y1={dotY} y2={dotY} stroke="#4a3326" strokeWidth={1.5} opacity={lane.open ? 1 : 0.5} />
                    {dots.map(({ event, px, row }) => {
                      const active = event.slug === selected;
                      const half = (event.title.length * CHAR_W) / 2;
                      const anchor = px - half < 4 ? "start" : px + half > w - 4 ? "end" : "middle";
                      return (
                        <g
                          key={event.id}
                          transform={`translate(${px},${dotY})`}
                          role="button"
                          tabIndex={0}
                          aria-label={event.title}
                          aria-pressed={active}
                          className="cursor-pointer outline-none focus-visible:[&>circle]:stroke-[3]"
                          onClick={(e) => {
                            e.stopPropagation();
                            onSelect(event.slug);
                          }}
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
                  </g>
                );
              })}
            </>
          )}
        </svg>
        {laneDots.map(({ lane, index, dimmed }) => (
          <div
            key={lane.id}
            className="pointer-events-none absolute left-1 flex items-center gap-2"
            style={{ top: index * laneH + 4, opacity: dimmed ? 0.5 : 1 }}
          >
            <span className="rounded bg-parchment/90 px-2 py-0.5 font-serif text-sm font-bold">{lane.name}</span>
            {lane.id !== NO_TRACK &&
              (lane.open ? (
                <button
                  className="pointer-events-auto rounded border border-mocha bg-parchment/90 px-2 text-xs"
                  aria-pressed={focus === lane.id}
                  onClick={() => toggleFocus(lane.id)}
                >
                  {focus === lane.id ? t("timeline.unfocus") : t("timeline.focus")}
                </button>
              ) : (
                <span className="rounded bg-parchment/90 px-2 text-xs">{t("timeline.laneLocked")}</span>
              ))}
          </div>
        ))}
        {popupDot && popupWidth > 0 && (
          <div
            className="absolute z-10 overflow-y-auto rounded border border-cappuccino bg-parchment p-3 shadow-lg"
            style={{
              left: popupPosition(popupDot.px, w, popupWidth).left,
              width: popupWidth,
              ...(popupSide(popupDot.dotY) === "above"
                ? { bottom: svgH - popupDot.dotY + 16, maxHeight: popupDot.dotY - 24 }
                : { top: popupDot.dotY + 16, maxHeight: svgH - popupDot.dotY - 40 }),
            }}
          >
            <EventPopup event={popupDot.event} onClose={() => onSelect(null)} />
            <span
              aria-hidden
              className={`absolute h-3 w-3 rotate-45 border-cappuccino bg-parchment ${
                popupSide(popupDot.dotY) === "above" ? "-bottom-[7px] border-b border-r" : "-top-[7px] border-l border-t"
              }`}
              style={{ left: popupPosition(popupDot.px, w, popupWidth).arrow - 6 }}
            />
          </div>
        )}
        </div>
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

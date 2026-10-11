import { useRef } from "react";
import { useTranslation } from "react-i18next";
import type { Timeline } from "../../api/client";
import { MAX_ZOOM, toYear } from "./layout";

interface Props {
  full: [number, number];
  events: Timeline["events"];
  /** The year span the chart currently shows. */
  visible: [number, number];
  onChange: (from: number, to: number) => void;
}

type Drag = { mode: "pan" | "left" | "right"; startX: number; from: number; to: number };

/** Overview bar of the whole period. The window shows what the chart shows: drag it to pan,
 * drag its edges to zoom, click the bar to jump there. */
export default function TimelineScrubber({ full, events, visible, onChange }: Props) {
  const { t } = useTranslation();
  const trackRef = useRef<HTMLDivElement>(null);
  const drag = useRef<Drag | null>(null);
  const span = full[1] - full[0];
  const minSpan = span / MAX_ZOOM;
  const [from, to] = visible;
  const pct = (year: number) => `${((year - full[0]) / span) * 100}%`;

  const yearsPerPx = () => span / (trackRef.current?.clientWidth || 1);

  function begin(event: React.PointerEvent, mode: Drag["mode"]) {
    event.stopPropagation(); // keep the track's click-to-jump out of it
    event.currentTarget.setPointerCapture(event.pointerId);
    drag.current = { mode, startX: event.clientX, from, to };
  }

  function move(event: React.PointerEvent) {
    const d = drag.current;
    if (!d) return;
    const delta = (event.clientX - d.startX) * yearsPerPx();
    if (d.mode === "pan") onChange(d.from + delta, d.to + delta);
    else if (d.mode === "left") onChange(Math.min(d.from + delta, d.to - minSpan), d.to);
    else onChange(d.from, Math.max(d.to + delta, d.from + minSpan));
  }

  function jump(event: React.PointerEvent) {
    const rect = trackRef.current!.getBoundingClientRect();
    const centre = full[0] + ((event.clientX - rect.left) / rect.width) * span;
    const half = (to - from) / 2;
    onChange(centre - half, centre + half);
  }

  function onKeyDown(event: React.KeyboardEvent) {
    const step = (to - from) / 10;
    if (event.key === "ArrowLeft") onChange(from - step, to - step);
    else if (event.key === "ArrowRight") onChange(from + step, to + step);
    else return;
    event.preventDefault();
  }

  const end = () => (drag.current = null);

  return (
    <div
      ref={trackRef}
      onPointerDown={jump}
      className="relative mt-3 h-12 shrink-0 cursor-pointer rounded border border-cappuccino bg-white/40"
    >
      {events.map((e) => (
        <span
          key={e.id}
          className="pointer-events-none absolute top-1/2 h-2 w-2 -translate-x-1/2 -translate-y-1/2 rounded-full bg-mocha/60"
          style={{ left: pct(toYear(e.event_date)) }}
        />
      ))}
      <div
        role="slider"
        tabIndex={0}
        aria-label={t("timeline.scrubber")}
        aria-valuemin={Math.round(full[0])}
        aria-valuemax={Math.round(full[1])}
        aria-valuenow={Math.round(from)}
        aria-valuetext={`${Math.round(from)}–${Math.round(to)}`}
        onKeyDown={onKeyDown}
        onPointerDown={(e) => begin(e, "pan")}
        onPointerMove={move}
        onPointerUp={end}
        onPointerCancel={end}
        className="absolute inset-y-0 cursor-grab touch-none rounded border-2 border-mocha bg-cappuccino/30 active:cursor-grabbing"
        style={{ left: pct(from), width: `${((to - from) / span) * 100}%` }}
      >
        {(["left", "right"] as const).map((side) => (
          <div
            key={side}
            onPointerDown={(e) => begin(e, side)}
            aria-hidden
            className={`absolute inset-y-0 w-2 cursor-ew-resize bg-mocha ${side === "left" ? "-left-1" : "-right-1"}`}
          />
        ))}
      </div>
    </div>
  );
}

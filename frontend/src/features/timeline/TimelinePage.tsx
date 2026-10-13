import { useQuery } from "@tanstack/react-query";
import { useState } from "react";
import { useTranslation } from "react-i18next";
import { Link } from "react-router-dom";
import { api } from "../../api/client";
import QueryStatus from "../../components/Status";
import TimelineChart from "./TimelineChart";

export default function TimelinePage() {
  const { t } = useTranslation();
  const timeline = useQuery({ queryKey: ["timeline"], queryFn: api.timeline });
  const [selected, setSelected] = useState<string | null>(null);
  const [focus, setFocus] = useState<number | null>(null);
  const focused = timeline.data?.tracks.find((track) => track.id === focus);

  return (
    <section className="flex h-full min-h-0 flex-col">
      <h1 className="sr-only">{t("timeline.title")}</h1>
      <QueryStatus query={timeline} />
      {focused && (
        <p className="mb-2 flex flex-wrap items-center gap-3 text-sm">
          <span className="font-semibold">{t("timeline.focused", { name: focused.name })}</span>
          <Link to={`/session?track=${focused.id}`} className="rounded border border-mocha px-3 py-0.5">
            {t("timeline.startSession")}
          </Link>
          <button className="underline" onClick={() => setFocus(null)}>
            {t("timeline.showAll")}
          </button>
        </p>
      )}
      {timeline.data && (
        <TimelineChart
          timeline={timeline.data}
          selected={selected}
          onSelect={setSelected}
          focus={focus}
          onFocus={setFocus}
        />
      )}
    </section>
  );
}

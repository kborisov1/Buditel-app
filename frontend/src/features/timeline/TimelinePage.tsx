import { useQuery } from "@tanstack/react-query";
import { useState } from "react";
import { useTranslation } from "react-i18next";
import { Link } from "react-router-dom";
import { api } from "../../api/client";
import QueryStatus from "../../components/Status";
import { formatEventDate } from "../entry/format";
import TimelineChart from "./TimelineChart";

export default function TimelinePage() {
  const { t } = useTranslation();
  const timeline = useQuery({ queryKey: ["timeline"], queryFn: api.timeline });
  const [selected, setSelected] = useState<string | null>(null);
  const current = timeline.data?.events.find((e) => e.slug === selected);

  return (
    <section>
      <h1 className="mb-4 font-serif text-3xl">{t("timeline.title")}</h1>
      <QueryStatus query={timeline} />
      {timeline.data && (
        <div className="grid gap-6 lg:grid-cols-[1fr_20rem]">
          <TimelineChart timeline={timeline.data} selected={selected} onSelect={setSelected} />
          {current && (
            <aside className="h-fit rounded border border-cappuccino bg-white/40 p-4">
              <button className="float-right text-sm underline" onClick={() => setSelected(null)}>
                {t("timeline.close")}
              </button>
              <h2 className="font-serif text-2xl">{current.title}</h2>
              <p className="text-sm">
                {formatEventDate(current.event_date, current.date_certainty, t)}
              </p>
              {current.locked ? (
                <p className="mt-3">🔒 {t("common.locked")}</p>
              ) : (
                <>
                  {current.region && <p className="mt-2 text-sm">{current.region}</p>}
                  <p className="mt-2">{current.summary}</p>
                  <Link
                    to={`/entries/${current.slug}`}
                    className="mt-4 block rounded bg-mocha px-4 py-3 text-center text-parchment"
                  >
                    {t("timeline.open")}
                  </Link>
                  {current.progress ? (
                    <Link
                      to={`/entries/${current.slug}/quiz`}
                      className="mt-2 block rounded border border-mocha px-4 py-2 text-center"
                    >
                      {t("timeline.quiz")}
                    </Link>
                  ) : (
                    <button
                      disabled
                      title={t("timeline.quizHint")}
                      className="mt-2 block w-full rounded border border-mocha px-4 py-2 opacity-40"
                    >
                      {t("timeline.quiz")}
                    </button>
                  )}
                </>
              )}
            </aside>
          )}
        </div>
      )}
    </section>
  );
}

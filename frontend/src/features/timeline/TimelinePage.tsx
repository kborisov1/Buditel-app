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
    <section className="flex h-full min-h-0 flex-col">
      <h1 className="sr-only">{t("timeline.title")}</h1>
      <QueryStatus query={timeline} />
      {timeline.data && (
        <div className="relative min-h-0 flex-1">
          <TimelineChart
            timeline={timeline.data}
            selected={selected}
            onSelect={setSelected}
          />
          {current && (
            <aside className="absolute bottom-16 right-0 top-10 z-10 w-80 max-w-full overflow-y-auto rounded border border-cappuccino bg-parchment p-4 shadow-lg">
              <button
                className="float-right text-sm underline"
                onClick={() => setSelected(null)}
              >
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
                  {current.region && (
                    <p className="mt-2 text-sm">{current.region}</p>
                  )}
                  <p className="mt-2">{current.summary}</p>
                  <Link
                    to={`/entries/${current.slug}`}
                    className="mt-4 block rounded bg-mocha px-4 py-3 text-center text-parchment"
                  >
                    {t("timeline.open")}
                  </Link>
                  {current.progress === "in_progress" ? (
                    <Link
                      to={`/entries/${current.slug}/quiz`}
                      className="mt-2 block rounded border border-mocha px-4 py-2 text-center"
                    >
                      {t("timeline.quiz")}
                    </Link>
                  ) : (
                    <button
                      disabled
                      title={
                        current.progress === null
                          ? t("timeline.quizHint")
                          : t("timeline.quizTaken")
                      }
                      className="mt-2 block w-full rounded border border-mocha px-4 py-2 opacity-40"
                    >
                      {current.progress === null
                        ? t("timeline.quiz")
                        : t("timeline.quizTaken")}
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

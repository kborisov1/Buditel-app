import { useMemo, useState } from "react";
import { useTranslation } from "react-i18next";
import { Link } from "react-router-dom";
import type { EntryListItem } from "../../api/client";
import QueryStatus from "../../components/Status";
import { formatEventDate } from "../entry/format";
import { useEntries } from "../entry/useEntries";

/** Interim layout: events by year with the side panel from scope 7.2. The zoomable D3
 * timeline (architecture 8) replaces the list and keeps the panel. */
export default function TimelinePage() {
  const { t } = useTranslation();
  const events = useEntries({ type: "event" });
  const [selected, setSelected] = useState<string | null>(null);

  const byYear = useMemo(() => {
    const sorted = [...(events.data ?? [])].sort((a, b) =>
      (a.event_date ?? "").localeCompare(b.event_date ?? ""),
    );
    const groups = new Map<string, EntryListItem[]>();
    for (const e of sorted) {
      const year = e.event_date?.slice(0, 4) ?? "";
      groups.set(year, [...(groups.get(year) ?? []), e]);
    }
    return [...groups];
  }, [events.data]);

  const current = events.data?.find((e) => e.slug === selected);

  return (
    <section>
      <h1 className="font-serif text-3xl">{t("timeline.title")}</h1>
      <p className="mb-4 text-sm">{t("timeline.note")}</p>
      <QueryStatus query={events} />
      <div className="grid gap-6 lg:grid-cols-[1fr_20rem]">
        <ol className="flex flex-col gap-4 border-l-2 border-cappuccino pl-4">
          {byYear.map(([year, items]) => (
            <li key={year}>
              <h2 className="font-serif text-xl font-semibold">{year}</h2>
              <ul className="mt-1 flex flex-col gap-1">
                {items.map((e) => (
                  <li key={e.id}>
                    <button
                      onClick={() => setSelected(e.slug)}
                      aria-pressed={selected === e.slug}
                      className={`w-full rounded px-3 py-2 text-left ${
                        selected === e.slug ? "bg-mocha text-parchment" : "hover:bg-cappuccino/30"
                      } ${e.locked ? "opacity-60" : ""}`}
                    >
                      {e.locked && "🔒 "}
                      {e.title}
                    </button>
                  </li>
                ))}
              </ul>
            </li>
          ))}
        </ol>
        {current && (
          <aside className="h-fit rounded border border-cappuccino bg-white/40 p-4 lg:sticky lg:top-4">
            <button className="float-right text-sm underline" onClick={() => setSelected(null)}>
              {t("timeline.close")}
            </button>
            <h2 className="font-serif text-2xl">{current.title}</h2>
            <p className="text-sm">
              {formatEventDate(
                current.event_date,
                current.locked ? undefined : current.date_certainty,
                t,
              )}
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
    </section>
  );
}

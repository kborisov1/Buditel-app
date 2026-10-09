import { useTranslation } from "react-i18next";
import { useSearchParams } from "react-router-dom";
import EntryRow from "../../components/EntryRow";
import QueryStatus from "../../components/Status";
import { useEntries } from "../entry/useEntries";

const TYPES = ["event", "person", "place", "institution", "work", "concept"] as const;

export default function LibraryPage() {
  const { t } = useTranslation();
  const [params, setParams] = useSearchParams();
  const type = params.get("type") ?? undefined;
  const q = params.get("q") ?? undefined;
  const entries = useEntries({ type, q });

  function setFilter(key: "type" | "q", value: string) {
    const next = new URLSearchParams(params);
    if (value) next.set(key, value);
    else next.delete(key);
    setParams(next);
  }

  const tab = (active: boolean) =>
    `rounded px-3 py-1 ${active ? "bg-mocha text-parchment" : "border border-cappuccino hover:bg-cappuccino/30"}`;

  return (
    <section>
      <h1 className="mb-4 font-serif text-3xl">{t("library.title")}</h1>
      <div className="mb-4 flex flex-wrap items-center gap-2">
        <button className={tab(!type)} onClick={() => setFilter("type", "")}>
          {t("library.all")}
        </button>
        {TYPES.map((value) => (
          <button
            key={value}
            className={tab(type === value)}
            onClick={() => setFilter("type", value)}
          >
            {t(`entryTypePlural.${value}`)}
          </button>
        ))}
        <input
          type="search"
          aria-label={t("library.search")}
          placeholder={t("library.search")}
          value={q ?? ""}
          onChange={(e) => setFilter("q", e.target.value)}
          className="ml-auto rounded border border-cappuccino bg-white/60 px-3 py-1"
        />
      </div>
      <QueryStatus query={entries} />
      {entries.data &&
        (entries.data.length === 0 ? (
          <p>{t("common.empty")}</p>
        ) : (
          <>
            <p className="mb-2 text-sm">{t("library.results", { count: entries.data.length })}</p>
            <ul className="flex flex-col gap-2">
              {entries.data.map((entry) => (
                <EntryRow key={entry.id} entry={entry} />
              ))}
            </ul>
          </>
        ))}
    </section>
  );
}

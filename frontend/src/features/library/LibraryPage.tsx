import { useQuery } from "@tanstack/react-query";
import { useTranslation } from "react-i18next";
import { useSearchParams } from "react-router-dom";
import { api } from "../../api/client";
import EntryRow from "../../components/EntryRow";
import QueryStatus from "../../components/Status";
import { useEntries } from "../entry/useEntries";

const TYPES = ["event", "person", "place", "institution", "work", "concept"] as const;

export default function LibraryPage() {
  const { t } = useTranslation();
  const [params, setParams] = useSearchParams();
  const type = params.get("type") ?? undefined;
  const q = params.get("q") ?? undefined;
  const track = params.get("track") ?? undefined;
  const phase = params.get("phase") ?? undefined;
  const region = params.get("region") ?? undefined;
  const entries = useEntries({ type, q, track, phase, region });

  // Options for the filters: tracks (themes) and phases (periods) from the API, regions from
  // the entries the user can see (a locked entry's region is not sent, scope 3.4).
  const tracks = useQuery({ queryKey: ["profile"], queryFn: api.profile });
  const timeline = useQuery({ queryKey: ["timeline"], queryFn: api.timeline });
  const everything = useEntries();
  const regions = [
    ...new Set(
      (everything.data ?? []).flatMap((e) => (!e.locked && e.region ? [e.region] : [])),
    ),
  ].sort((a, b) => a.localeCompare(b, "bg"));
  const filtered = !!(type || q || track || phase || region);

  function setFilter(key: "type" | "q" | "track" | "phase" | "region", value: string) {
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
      <div className="mb-4 flex flex-wrap items-end gap-4">
        <FilterSelect
          label={t("library.track")}
          value={track}
          options={(tracks.data?.tracks ?? []).map((tr) => ({ value: String(tr.id), label: tr.name }))}
          onChange={(v) => setFilter("track", v)}
        />
        <FilterSelect
          label={t("library.phase")}
          value={phase}
          options={(timeline.data?.phases ?? []).map((p) => ({ value: String(p.id), label: p.name }))}
          onChange={(v) => setFilter("phase", v)}
        />
        <FilterSelect
          label={t("library.region")}
          value={region}
          options={regions.map((r) => ({ value: r, label: r }))}
          onChange={(v) => setFilter("region", v)}
        />
        {filtered && (
          <button className="underline" onClick={() => setParams(new URLSearchParams())}>
            {t("library.reset")}
          </button>
        )}
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

function FilterSelect({
  label,
  value,
  options,
  onChange,
}: {
  label: string;
  value: string | undefined;
  options: { value: string; label: string }[];
  onChange: (value: string) => void;
}) {
  const { t } = useTranslation();
  return (
    <label className="flex flex-col gap-1 text-sm">
      {label}
      <select
        value={value ?? ""}
        onChange={(e) => onChange(e.target.value)}
        className="rounded border border-cappuccino bg-white/60 px-3 py-1"
      >
        <option value="">{t("library.anyFilter")}</option>
        {options.map((o) => (
          <option key={o.value} value={o.value}>
            {o.label}
          </option>
        ))}
      </select>
    </label>
  );
}

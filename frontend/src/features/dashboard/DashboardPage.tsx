import { useTranslation } from "react-i18next";
import { Link } from "react-router-dom";
import QueryStatus from "../../components/Status";
import { useEntries } from "../entry/useEntries";

/** Panels backed by endpoints that do not exist yet are marked as coming soon (architecture 4). */
const PENDING_PANELS = ["goal", "streak", "reviews", "level"] as const;

function Panel({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <section className="rounded border border-cappuccino bg-white/40 p-4">
      <h2 className="mb-2 font-serif text-xl">{title}</h2>
      {children}
    </section>
  );
}

export default function DashboardPage() {
  const { t } = useTranslation();
  const entries = useEntries();
  const unlocked = (entries.data ?? []).filter((e) => !e.locked);
  const inProgress = unlocked.filter((e) => e.progress === "in_progress");
  const next = unlocked.filter((e) => e.type === "event" && e.progress === null).slice(0, 5);

  return (
    <div>
      <h1 className="mb-4 font-serif text-3xl">{t("dashboard.title")}</h1>
      <div className="mb-6 flex flex-wrap gap-3">
        <button disabled title={t("common.comingSoon")} className="rounded bg-mocha px-5 py-2 text-parchment opacity-50">
          {t("dashboard.startSession")}
        </button>
        <button disabled className="rounded border border-mocha px-4 py-2 opacity-50">
          {t("dashboard.reviewOnly")}
        </button>
        <Link to="/library" className="rounded border border-mocha px-4 py-2">
          {t("dashboard.continueReading")}
        </Link>
        <Link to="/practice" className="rounded border border-mocha px-4 py-2">
          {t("dashboard.practice")}
        </Link>
      </div>
      <QueryStatus query={entries} />
      <div className="grid gap-4 md:grid-cols-2">
        <Panel title={t("dashboard.continue")}>
          {inProgress.length === 0 ? (
            <p>{t("dashboard.nothingToContinue")}</p>
          ) : (
            <ul className="list-disc pl-5">
              {inProgress.map((e) => (
                <li key={e.id}>
                  <Link to={`/entries/${e.slug}`} className="underline">
                    {e.title}
                  </Link>
                </li>
              ))}
            </ul>
          )}
        </Panel>
        <Panel title={t("dashboard.next")}>
          <ul className="list-disc pl-5">
            {next.map((e) => (
              <li key={e.id}>
                <Link to={`/entries/${e.slug}`} className="underline">
                  {e.title}
                </Link>
              </li>
            ))}
          </ul>
        </Panel>
        {PENDING_PANELS.map((key) => (
          <Panel key={key} title={t(`dashboard.${key}`)}>
            <p className="opacity-60">{t("common.comingSoon")}</p>
          </Panel>
        ))}
      </div>
    </div>
  );
}

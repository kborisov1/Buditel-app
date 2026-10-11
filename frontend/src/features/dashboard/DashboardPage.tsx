import { useQuery } from "@tanstack/react-query";
import { useTranslation } from "react-i18next";
import { Link } from "react-router-dom";
import { api } from "../../api/client";
import QueryStatus from "../../components/Status";
import { useEntries } from "../entry/useEntries";
import { LevelBar, StreakText } from "./parts";

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
  const dashboard = useQuery({ queryKey: ["dashboard"], queryFn: api.dashboard });
  const entries = useEntries();
  const d = dashboard.data;
  const unlocked = (entries.data ?? []).filter((e) => !e.locked);
  const inProgress = unlocked.filter((e) => e.progress === "in_progress");

  const primary = "rounded bg-mocha px-5 py-2 text-parchment";
  const secondary = "rounded border border-mocha px-4 py-2";

  return (
    <div>
      <h1 className="mb-4 font-serif text-3xl">{t("dashboard.title")}</h1>
      <div className="mb-6 flex flex-wrap gap-3">
        <Link to="/session" className={primary}>
          {t("dashboard.startSession")}
        </Link>
        <Link to="/review" className={secondary}>
          {t("dashboard.reviewOnly")}
        </Link>
        <Link to="/library" className={secondary}>
          {t("dashboard.continueReading")}
        </Link>
        <Link to="/practice" className={secondary}>
          {t("dashboard.practice")}
        </Link>
        <Link to="/challenge" className={secondary}>
          {t("dashboard.challenge")}
        </Link>
      </div>
      <QueryStatus query={dashboard} />
      {d && (
        <div className="grid gap-4 md:grid-cols-2">
          <Panel title={t("dashboard.goal")}>
            <progress
              className="h-3 w-full"
              value={Math.min(d.goal.earned_today, d.goal.target)}
              max={d.goal.target}
              aria-label={t("dashboard.goal")}
            />
            <p className="text-sm">
              {d.goal.earned_today} / {d.goal.target} XP
              {d.goal.reached && ` · ✓ ${t("dashboard.goalReached")}`}
            </p>
          </Panel>
          <Panel title={t("dashboard.streak")}>
            <StreakText streak={d.streak} />
          </Panel>
          <Panel title={t("dashboard.reviews")}>
            <p className="text-2xl">{d.reviews_due}</p>
            {d.reviews_due > 0 && (
              <Link to="/review" className="underline">
                {t("dashboard.reviewOnly")}
              </Link>
            )}
          </Panel>
          <Panel title={t("dashboard.level")}>
            <LevelBar level={d.level} />
          </Panel>
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
        </div>
      )}
    </div>
  );
}

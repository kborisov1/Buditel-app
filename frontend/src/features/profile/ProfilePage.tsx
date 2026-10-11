import { useQuery } from "@tanstack/react-query";
import { useTranslation } from "react-i18next";
import { Link } from "react-router-dom";
import { api } from "../../api/client";
import QueryStatus from "../../components/Status";
import { LevelBar, StreakText } from "../dashboard/parts";

export default function ProfilePage() {
  const { t } = useTranslation();
  const profile = useQuery({ queryKey: ["profile"], queryFn: api.profile });
  const p = profile.data;

  return (
    <section>
      <h1 className="mb-4 font-serif text-3xl">{t("nav.profile")}</h1>
      <QueryStatus query={profile} />
      {p && (
        <div className="grid gap-6 md:grid-cols-2">
          <div className="rounded border border-cappuccino bg-white/40 p-4">
            <p className="text-sm">{p.email}</p>
            <LevelBar level={p.level} />
            <StreakText streak={p.streak} />
          </div>
          <div className="rounded border border-cappuccino bg-white/40 p-4">
            <h2 className="mb-2 font-serif text-xl">{t("profile.tracks")}</h2>
            <ul className="flex flex-col gap-2">
              {p.tracks.map((tr) => (
                <li key={tr.id}>
                  <div className="flex justify-between text-sm">
                    <span>{tr.name}</span>
                    <span>
                      {tr.read} / {tr.total}
                    </span>
                  </div>
                  <progress
                    className="h-2 w-full"
                    value={tr.read}
                    max={Math.max(tr.total, 1)}
                    aria-label={tr.name}
                  />
                </li>
              ))}
            </ul>
          </div>
          <div className="rounded border border-cappuccino bg-white/40 p-4 md:col-span-2">
            <h2 className="mb-2 font-serif text-xl">{t("profile.history")}</h2>
            {p.history.length === 0 ? (
              <p>{t("profile.noHistory")}</p>
            ) : (
              <table className="w-full text-left text-sm">
                <thead>
                  <tr>
                    <th>{t("profile.when")}</th>
                    <th>{t("profile.what")}</th>
                    <th>{t("profile.result")}</th>
                    <th>XP</th>
                  </tr>
                </thead>
                <tbody>
                  {p.history.map((h, i) => (
                    <tr key={i} className="border-t border-cappuccino/40">
                      <td>{new Date(h.at).toLocaleString("bg-BG")}</td>
                      <td>
                        {t(`profile.kind.${h.kind}`)}
                        {h.entry && (
                          <>
                            {": "}
                            <Link to={`/entries/${h.entry.slug}`} className="underline">
                              {h.entry.title}
                            </Link>
                          </>
                        )}
                      </td>
                      <td>
                        {h.score}/{h.total}
                        {h.passed !== null && ` · ${h.passed ? t("quiz.correct") : t("quiz.incorrect")}`}
                      </td>
                      <td>{h.xp_awarded}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </div>
        </div>
      )}
    </section>
  );
}

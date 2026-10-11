import { useQuery } from "@tanstack/react-query";
import { useTranslation } from "react-i18next";
import { Link } from "react-router-dom";
import { api, type SessionStep } from "../../api/client";
import QueryStatus from "../../components/Status";

/** Where a step leads. A planned check has no target yet (it opens after the entry). */
export function stepTarget(step: SessionStep): string | null {
  if (step.kind === "review") return "/review";
  if (step.kind === "check") return step.check_id === null ? null : `/checks/${step.check_id}`;
  return `/entries/${step.slug}`;
}

export default function SessionPage() {
  const { t } = useTranslation();
  const session = useQuery({ queryKey: ["session"], queryFn: api.session });
  const steps = session.data?.steps ?? [];

  return (
    <section>
      <h1 className="mb-1 font-serif text-3xl">{t("session.title")}</h1>
      <p className="mb-4 text-sm">{t("session.hint")}</p>
      <QueryStatus query={session} />
      {session.data && steps.length === 0 && <p>{t("session.empty")}</p>}
      <ol className="flex flex-col gap-2">
        {steps.map((step, i) => {
          const target = stepTarget(step);
          const label =
            step.kind === "review"
              ? t("session.review", { count: step.count })
              : step.kind === "check"
                ? t(step.check_id === null ? "session.checkPlanned" : "session.check")
                : step.title;
          const body = (
            <>
              <span className="mr-3 font-semibold">{i + 1}.</span>
              {label}
              {step.kind === "entry" && (
                <span className="ml-3 text-sm">
                  {t(`entryType.${step.type}`)}
                  {step.progress && ` · ${t(`progress.${step.progress}`)}`}
                </span>
              )}
            </>
          );
          return (
            <li key={i}>
              {target ? (
                <Link
                  to={target}
                  className="block rounded border border-cappuccino bg-white/40 px-4 py-3 hover:bg-white/70"
                >
                  {body}
                </Link>
              ) : (
                <div className="rounded border border-cappuccino/40 px-4 py-3 opacity-60">
                  {body}
                </div>
              )}
            </li>
          );
        })}
      </ol>
    </section>
  );
}

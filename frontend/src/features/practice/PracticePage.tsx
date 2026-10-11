import { useMutation, useQuery } from "@tanstack/react-query";
import { useState } from "react";
import { useTranslation } from "react-i18next";
import { api } from "../../api/client";
import QueryStatus from "../../components/Status";
import { useRefreshLearnerData } from "../progress";
import QuestionStepper from "../quiz/QuestionStepper";

const field = "rounded border border-cappuccino bg-white/60 px-3 py-1";

export default function PracticePage() {
  const { t } = useTranslation();
  const refresh = useRefreshLearnerData();
  const profile = useQuery({ queryKey: ["profile"], queryFn: api.profile });
  const timeline = useQuery({ queryKey: ["timeline"], queryFn: api.timeline });
  const [track, setTrack] = useState("");
  const [phase, setPhase] = useState("");
  const [count, setCount] = useState(10);
  const [round, setRound] = useState(0);

  const start = useMutation({
    mutationFn: () =>
      api.practice({
        track: track ? Number(track) : undefined,
        phase: phase ? Number(phase) : undefined,
        count,
      }),
    onSuccess: () => setRound((n) => n + 1),
  });
  const questions = start.data?.questions;

  return (
    <section>
      <h1 className="mb-4 font-serif text-3xl">{t("practice.title")}</h1>
      {!questions && (
        <form
          className="flex flex-wrap items-end gap-4"
          onSubmit={(e) => {
            e.preventDefault();
            start.mutate();
          }}
        >
          <label className="flex flex-col gap-1">
            {t("practice.track")}
            <select className={field} value={track} onChange={(e) => setTrack(e.target.value)}>
              <option value="">{t("practice.any")}</option>
              {profile.data?.tracks.map((tr) => (
                <option key={tr.id} value={tr.id}>
                  {tr.name}
                </option>
              ))}
            </select>
          </label>
          <label className="flex flex-col gap-1">
            {t("practice.phase")}
            <select className={field} value={phase} onChange={(e) => setPhase(e.target.value)}>
              <option value="">{t("practice.any")}</option>
              {timeline.data?.phases.map((p) => (
                <option key={p.id} value={p.id}>
                  {p.name}
                </option>
              ))}
            </select>
          </label>
          <label className="flex flex-col gap-1">
            {t("practice.count")}
            <input
              type="number"
              min={1}
              max={50}
              value={count}
              onChange={(e) => setCount(Math.min(50, Math.max(1, Number(e.target.value) || 1)))}
              className={`${field} w-24`}
            />
          </label>
          <button
            type="submit"
            disabled={start.isPending}
            className="rounded bg-mocha px-5 py-2 text-parchment disabled:opacity-60"
          >
            {t("practice.start")}
          </button>
        </form>
      )}
      {start.isError && <p role="alert">{t("common.error")}</p>}
      <QueryStatus query={profile} />
      {questions &&
        (questions.length === 0 ? (
          <div>
            <p>{t("practice.empty")}</p>
            <button className="underline" onClick={() => start.reset()}>
              {t("practice.again")}
            </button>
          </div>
        ) : (
          <QuestionStepper
            key={round}
            questions={questions}
            onFinish={() => void refresh()}
            onAnswer={async (question, answer) => {
              const r = await api.answerPractice(question.id, answer);
              return {
                correct: r.correct,
                explanation: r.explanation,
                xp: r.xp_awarded,
                correctAnswer: r.correct_answer,
              };
            }}
            finished={
              <button className="mt-4 underline" onClick={() => start.reset()}>
                {t("practice.again")}
              </button>
            }
          />
        ))}
    </section>
  );
}

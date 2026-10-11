import { useMutation, useQuery } from "@tanstack/react-query";
import { useState } from "react";
import { useTranslation } from "react-i18next";
import { Link, useParams } from "react-router-dom";
import { api, ApiError, type QuizAnswer } from "../../api/client";
import QueryStatus from "../../components/Status";
import { useRefreshLearnerData } from "../progress";
import QuestionInput, { initialAnswer, isAnswered } from "../quiz/QuestionInput";
import ResultList from "../quiz/ResultList";

/** Older-event check (scope 4.1): all questions, then graded together. No pass mark. */
export default function CheckPage() {
  const { t } = useTranslation();
  const id = Number(useParams().id);
  const refresh = useRefreshLearnerData();
  const check = useQuery({
    queryKey: ["check", id],
    queryFn: () => api.check(id),
    staleTime: Infinity,
    gcTime: 0,
    retry: false,
  });
  const [answers, setAnswers] = useState<Record<number, QuizAnswer | undefined>>({});
  const questions = check.data?.questions ?? [];
  const value = (qid: number, i: number) => answers[qid] ?? initialAnswer(questions[i]);

  const submit = useMutation({
    mutationFn: () =>
      api.submitCheck(
        id,
        questions.map((q, i) => ({ question_id: q.id, answer: value(q.id, i)! })),
      ),
    onSuccess: () => void refresh(),
  });

  if (check.error instanceof ApiError && check.error.status === 409) {
    return <p>{t("check.closed")}</p>;
  }
  if (!check.data) return <QueryStatus query={check} />;

  if (submit.data) {
    return (
      <section>
        <h1 className="font-serif text-3xl">{t("check.title")}</h1>
        <p className="mt-2">
          {t("quiz.score", { score: submit.data.score, total: submit.data.total })}
        </p>
        <p>{t("quiz.xp", { xp: submit.data.xp_awarded })}</p>
        <ResultList questions={questions} results={submit.data.results} />
        <Link to="/" className="mt-6 inline-block underline">
          {t("common.toDashboard")}
        </Link>
      </section>
    );
  }

  const complete = questions.every((q, i) => isAnswered(q, value(q.id, i)));
  return (
    <section>
      <h1 className="mb-1 font-serif text-3xl">{t("check.title")}</h1>
      <p className="mb-4 text-sm">{t("check.hint")}</p>
      <form
        className="flex flex-col gap-6"
        onSubmit={(e) => {
          e.preventDefault();
          if (complete) submit.mutate();
        }}
      >
        {questions.map((q, i) => (
          <fieldset key={q.id} className="rounded border border-cappuccino p-4">
            <legend className="px-2 font-semibold">
              {i + 1}. {q.prompt}
            </legend>
            <QuestionInput
              question={q}
              value={value(q.id, i)}
              onChange={(v) => setAnswers((prev) => ({ ...prev, [q.id]: v }))}
            />
          </fieldset>
        ))}
        {submit.isError && <p role="alert">{t("common.error")}</p>}
        <div>
          <button
            type="submit"
            disabled={!complete || submit.isPending}
            className="rounded bg-mocha px-5 py-2 text-parchment disabled:opacity-60"
          >
            {t("quiz.submit")}
          </button>
        </div>
      </form>
    </section>
  );
}

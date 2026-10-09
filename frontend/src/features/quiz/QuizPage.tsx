import { useMutation } from "@tanstack/react-query";
import { useEffect, useRef, useState } from "react";
import { useTranslation } from "react-i18next";
import { Link, useParams } from "react-router-dom";
import { api, ApiError, type Quiz, type QuizAnswer, type QuizResult } from "../../api/client";
import { useRefreshProgress } from "../entry/useEntries";
import QuestionInput, { initialAnswer, isAnswered } from "./QuestionInput";

const show = (answer: QuizAnswer): string =>
  Array.isArray(answer) ? answer.join(" → ") : String(answer);

export default function QuizPage() {
  const { t } = useTranslation();
  const { slug = "" } = useParams();
  const refresh = useRefreshProgress();
  const [quiz, setQuiz] = useState<Quiz | null>(null);
  const [answers, setAnswers] = useState<Record<number, QuizAnswer | undefined>>({});
  const [result, setResult] = useState<QuizResult | null>(null);

  const start = useMutation({
    mutationFn: () => api.startQuiz(slug),
    onSuccess: (data) => {
      setQuiz(data);
      setResult(null);
      setAnswers(Object.fromEntries(data.questions.map((q) => [q.id, initialAnswer(q)])));
    },
  });
  const submit = useMutation({
    mutationFn: () =>
      api.submitQuiz(
        quiz!.attempt_id,
        quiz!.questions.map((q) => ({ question_id: q.id, answer: answers[q.id]! })),
      ),
    onSuccess: (data) => {
      setResult(data);
      void refresh();
    },
  });

  // Start once on mount (the ref guards StrictMode's double effect).
  const started = useRef(false);
  useEffect(() => {
    if (started.current) return;
    started.current = true;
    start.mutate();
  }, [start]);

  const back = (
    <Link to={`/entries/${slug}`} className="underline">
      {t("quiz.backToEntry")}
    </Link>
  );

  if (start.isError) {
    const status = start.error instanceof ApiError ? start.error.status : 0;
    return (
      <section>
        <p role="alert">{status === 409 ? t("quiz.notReady") : t("common.error")}</p>
        {back}
      </section>
    );
  }
  if (!quiz) return <p>{t("common.loading")}</p>;

  if (result) {
    return (
      <section>
        <h1 className="font-serif text-3xl">
          {result.passed ? t("quiz.passed") : t("quiz.failed")}
        </h1>
        <p className="mt-2">{t("quiz.score", { score: result.score, total: result.total })}</p>
        {result.passed ? (
          <>
            <p>{t("quiz.xp", { xp: result.xp_awarded })}</p>
            <ol className="mt-6 flex flex-col gap-4">
              {result.results.map((r) => {
                const question = quiz.questions.find((q) => q.id === r.question_id);
                return (
                  <li key={r.question_id} className="rounded border border-cappuccino p-4">
                    <p className="font-semibold">{question?.prompt}</p>
                    <p>{r.correct ? `✓ ${t("quiz.correct")}` : `✗ ${t("quiz.incorrect")}`}</p>
                    <p className="text-sm">
                      {t("quiz.yourAnswer")}: {show(r.your_answer)}
                    </p>
                    {!r.correct && (
                      <p className="text-sm">
                        {t("quiz.correctAnswer")}: {show(r.correct_answer)}
                      </p>
                    )}
                    {r.explanation && <p className="mt-2">{r.explanation}</p>}
                  </li>
                );
              })}
            </ol>
          </>
        ) : (
          <p>{t("quiz.failedHint")}</p>
        )}
        <div className="mt-6 flex gap-4">
          {back}
          {!result.passed && (
            <button className="underline" onClick={() => start.mutate()}>
              {t("quiz.retry")}
            </button>
          )}
        </div>
      </section>
    );
  }

  const complete = quiz.questions.every((q) => isAnswered(q, answers[q.id]));
  return (
    <section>
      <h1 className="mb-4 font-serif text-3xl">{t("quiz.title")}</h1>
      <form
        onSubmit={(event) => {
          event.preventDefault();
          if (complete) submit.mutate();
        }}
        className="flex flex-col gap-6"
      >
        {quiz.questions.map((q, index) => (
          <fieldset key={q.id} className="rounded border border-cappuccino p-4">
            <legend className="px-2 font-semibold">
              {index + 1}. {q.prompt}
            </legend>
            <QuestionInput
              question={q}
              value={answers[q.id]}
              onChange={(value) => setAnswers((prev) => ({ ...prev, [q.id]: value }))}
            />
          </fieldset>
        ))}
        {!complete && <p className="text-sm">{t("quiz.answerAll")}</p>}
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

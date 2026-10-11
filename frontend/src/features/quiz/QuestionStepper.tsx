import { useState } from "react";
import { useTranslation } from "react-i18next";
import { Link } from "react-router-dom";
import type { QuizAnswer, QuizQuestion } from "../../api/client";
import QuestionInput, { initialAnswer, isAnswered } from "./QuestionInput";
import { showAnswer } from "./ResultList";

/** What the server said about one answered question. Fields differ per flow (scope 5, 7.5). */
export interface StepFeedback {
  correct: boolean;
  explanation: string;
  xp: number;
  correctAnswer?: QuizAnswer;
  /** Review only: a link back to the entry after a wrong answer (scope 5). */
  entry?: { slug: string; title: string } | null;
  note?: string;
}

interface Props {
  questions: QuizQuestion[];
  onAnswer: (question: QuizQuestion, answer: QuizAnswer) => Promise<StepFeedback>;
  onFinish?: () => void;
  finished: React.ReactNode;
}

/** One question at a time with feedback after each answer (review, practice, challenge). */
export default function QuestionStepper({ questions, onAnswer, onFinish, finished }: Props) {
  const { t } = useTranslation();
  const [index, setIndex] = useState(0);
  const [answer, setAnswer] = useState<QuizAnswer | undefined>(() =>
    questions[0] ? initialAnswer(questions[0]) : undefined,
  );
  const [feedback, setFeedback] = useState<StepFeedback | null>(null);
  const [busy, setBusy] = useState(false);
  const [failed, setFailed] = useState(false);
  const [stats, setStats] = useState({ correct: 0, xp: 0 });

  const question = questions[index];
  if (!question) {
    return (
      <div>
        <p className="font-serif text-2xl">{t("stepper.done")}</p>
        <p>{t("stepper.summary", { correct: stats.correct, total: questions.length })}</p>
        <p>{t("quiz.xp", { xp: stats.xp })}</p>
        {finished}
      </div>
    );
  }

  async function submit() {
    setBusy(true);
    setFailed(false);
    try {
      const result = await onAnswer(question, answer as QuizAnswer);
      setFeedback(result);
      setStats((s) => ({ correct: s.correct + (result.correct ? 1 : 0), xp: s.xp + result.xp }));
    } catch {
      setFailed(true);
    } finally {
      setBusy(false);
    }
  }

  function next() {
    const following = questions[index + 1];
    setIndex(index + 1);
    setFeedback(null);
    setAnswer(following ? initialAnswer(following) : undefined);
    if (!following) onFinish?.();
  }

  return (
    <div>
      <p className="mb-2 text-sm">{t("stepper.progress", { n: index + 1, total: questions.length })}</p>
      <fieldset key={question.id} className="rounded border border-cappuccino p-4" disabled={!!feedback}>
        <legend className="px-2 font-semibold">{question.prompt}</legend>
        <QuestionInput question={question} value={answer} onChange={setAnswer} />
      </fieldset>
      {failed && <p role="alert">{t("common.error")}</p>}
      {feedback ? (
        <div className="mt-4 rounded border border-cappuccino bg-white/40 p-4" role="status">
          <p className="font-semibold">
            {feedback.correct ? `✓ ${t("quiz.correct")}` : `✗ ${t("quiz.incorrect")}`}
            {feedback.xp > 0 && ` (+${feedback.xp})`}
          </p>
          {!feedback.correct && feedback.correctAnswer !== undefined && (
            <p className="text-sm">
              {t("quiz.correctAnswer")}: {showAnswer(feedback.correctAnswer)}
            </p>
          )}
          {feedback.explanation && <p className="mt-2">{feedback.explanation}</p>}
          {feedback.note && <p className="mt-1 text-sm">{feedback.note}</p>}
          {feedback.entry && (
            <Link to={`/entries/${feedback.entry.slug}`} className="mt-2 block underline">
              {t("stepper.reread", { title: feedback.entry.title })}
            </Link>
          )}
          <button onClick={next} className="mt-3 rounded bg-mocha px-5 py-2 text-parchment">
            {index + 1 < questions.length ? t("stepper.next") : t("stepper.finish")}
          </button>
        </div>
      ) : (
        <button
          onClick={() => void submit()}
          disabled={busy || !isAnswered(question, answer)}
          className="mt-4 rounded bg-mocha px-5 py-2 text-parchment disabled:opacity-60"
        >
          {t("stepper.answer")}
        </button>
      )}
    </div>
  );
}

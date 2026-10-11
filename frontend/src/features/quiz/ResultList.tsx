import { useTranslation } from "react-i18next";
import type { QuizAnswer, QuizQuestion } from "../../api/client";

interface Result {
  question_id: number;
  correct: boolean;
  your_answer: QuizAnswer;
  correct_answer: QuizAnswer;
  explanation: string;
}

export const showAnswer = (answer: QuizAnswer): string =>
  Array.isArray(answer) ? answer.join(" → ") : String(answer);

/** Per-question results with explanations, shown after a pass or a finished check. */
export default function ResultList({
  questions,
  results,
}: {
  questions: QuizQuestion[];
  results: Result[];
}) {
  const { t } = useTranslation();
  return (
    <ol className="mt-6 flex flex-col gap-4">
      {results.map((r) => (
        <li key={r.question_id} className="rounded border border-cappuccino p-4">
          <p className="font-semibold">{questions.find((q) => q.id === r.question_id)?.prompt}</p>
          <p>{r.correct ? `✓ ${t("quiz.correct")}` : `✗ ${t("quiz.incorrect")}`}</p>
          <p className="text-sm">
            {t("quiz.yourAnswer")}: {showAnswer(r.your_answer)}
          </p>
          {!r.correct && (
            <p className="text-sm">
              {t("quiz.correctAnswer")}: {showAnswer(r.correct_answer)}
            </p>
          )}
          {r.explanation && <p className="mt-2">{r.explanation}</p>}
        </li>
      ))}
    </ol>
  );
}

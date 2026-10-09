import { useTranslation } from "react-i18next";
import type { QuizAnswer, QuizQuestion } from "../../api/client";

interface Props {
  question: QuizQuestion;
  value: QuizAnswer | undefined;
  onChange: (value: QuizAnswer) => void;
}

/** One input per question type (architecture 5). Date ordering starts in the shown order. */
export default function QuestionInput({ question, value, onChange }: Props) {
  const { t } = useTranslation();
  const name = `q-${question.id}`;

  if (question.type === "multiple_choice") {
    return (
      <div className="flex flex-col gap-1">
        {(question.options ?? []).map((option, index) => (
          <label key={option} className="flex items-center gap-2">
            <input
              type="radio"
              name={name}
              checked={value === index}
              onChange={() => onChange(index)}
            />
            {option}
          </label>
        ))}
      </div>
    );
  }

  if (question.type === "true_false") {
    return (
      <div className="flex gap-4">
        {[true, false].map((option) => (
          <label key={String(option)} className="flex items-center gap-2">
            <input
              type="radio"
              name={name}
              checked={value === option}
              onChange={() => onChange(option)}
            />
            {option ? t("quiz.trueLabel") : t("quiz.falseLabel")}
          </label>
        ))}
      </div>
    );
  }

  if (question.type === "date_ordering") {
    const items = Array.isArray(value) ? value : (question.items ?? []);
    const move = (from: number, to: number) => {
      const next = [...items];
      next.splice(to, 0, next.splice(from, 1)[0]);
      onChange(next);
    };
    return (
      <div>
        <p className="mb-1 text-sm">{t("quiz.orderHint")}</p>
        <ol className="flex list-decimal flex-col gap-1 pl-6">
          {items.map((item, index) => (
            <li key={item}>
              <span className="mr-3">{item}</span>
              <button
                type="button"
                aria-label={`${t("quiz.moveUp")}: ${item}`}
                disabled={index === 0}
                onClick={() => move(index, index - 1)}
                className="rounded border border-cappuccino px-2 disabled:opacity-30"
              >
                ↑
              </button>{" "}
              <button
                type="button"
                aria-label={`${t("quiz.moveDown")}: ${item}`}
                disabled={index === items.length - 1}
                onClick={() => move(index, index + 1)}
                className="rounded border border-cappuccino px-2 disabled:opacity-30"
              >
                ↓
              </button>
            </li>
          ))}
        </ol>
      </div>
    );
  }

  return (
    <input
      type="text"
      aria-label={question.prompt}
      placeholder={t("quiz.blankPlaceholder")}
      value={typeof value === "string" ? value : ""}
      onChange={(e) => onChange(e.target.value)}
      className="rounded border border-cappuccino bg-white/60 p-2"
    />
  );
}

/** Date ordering counts as answered from the start (the shown order is a valid answer). */
export function isAnswered(question: QuizQuestion, value: QuizAnswer | undefined): boolean {
  if (question.type === "date_ordering") return true;
  if (question.type === "fill_blank") return typeof value === "string" && value.trim() !== "";
  return value !== undefined;
}

export function initialAnswer(question: QuizQuestion): QuizAnswer | undefined {
  return question.type === "date_ordering" ? (question.items ?? []) : undefined;
}

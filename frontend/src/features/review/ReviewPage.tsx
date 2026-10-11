import { useQuery } from "@tanstack/react-query";
import { useTranslation } from "react-i18next";
import { Link } from "react-router-dom";
import { api } from "../../api/client";
import QueryStatus from "../../components/Status";
import { useRefreshLearnerData } from "../progress";
import QuestionStepper from "../quiz/QuestionStepper";

export default function ReviewPage() {
  const { t } = useTranslation();
  const refresh = useRefreshLearnerData();
  // The queue is fixed for the visit; refetching mid-review would reshuffle the questions.
  const review = useQuery({
    queryKey: ["review"],
    queryFn: api.review,
    staleTime: Infinity,
    gcTime: 0,
  });

  return (
    <section>
      <h1 className="mb-4 font-serif text-3xl">{t("review.title")}</h1>
      <QueryStatus query={review} />
      {review.data &&
        (review.data.questions.length === 0 ? (
          <p>{t("review.empty")}</p>
        ) : (
          <QuestionStepper
            questions={review.data.questions}
            onFinish={() => void refresh()}
            onAnswer={async (question, answer) => {
              const r = await api.answerReview(question.id, answer);
              return {
                correct: r.correct,
                explanation: r.explanation,
                xp: r.xp_awarded,
                entry: r.entry,
                note: t("review.nextDue", {
                  date: new Date(`${r.next_due_date}T00:00:00`).toLocaleDateString("bg-BG"),
                }),
              };
            }}
            finished={<BackLink />}
          />
        ))}
    </section>
  );
}

function BackLink() {
  const { t } = useTranslation();
  return (
    <Link to="/" className="mt-4 inline-block underline">
      {t("common.toDashboard")}
    </Link>
  );
}

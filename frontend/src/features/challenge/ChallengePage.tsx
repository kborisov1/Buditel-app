import { useQuery } from "@tanstack/react-query";
import { useState } from "react";
import { useTranslation } from "react-i18next";
import { Link } from "react-router-dom";
import { api } from "../../api/client";
import QueryStatus from "../../components/Status";
import { useRefreshLearnerData } from "../progress";
import QuestionStepper from "../quiz/QuestionStepper";

export default function ChallengePage() {
  const { t } = useTranslation();
  const refresh = useRefreshLearnerData();
  const [bonus, setBonus] = useState(0);
  const challenge = useQuery({
    queryKey: ["daily-challenge"],
    queryFn: api.dailyChallenge,
    staleTime: Infinity,
    gcTime: 0,
  });
  const data = challenge.data;
  const open = data?.questions.filter((q) => !q.answered).map((q) => q.question) ?? [];

  return (
    <section>
      <h1 className="mb-4 font-serif text-3xl">{t("challenge.title")}</h1>
      <QueryStatus query={challenge} />
      {data &&
        (data.id === null ? (
          <p>{t("challenge.none")}</p>
        ) : open.length === 0 ? (
          <p>{t("challenge.completed")}</p>
        ) : (
          <QuestionStepper
            questions={open}
            onFinish={() => void refresh()}
            onAnswer={async (question, answer) => {
              const r = await api.answerChallenge(question.id, answer);
              setBonus((b) => b + r.bonus_xp);
              return {
                correct: r.correct,
                explanation: r.explanation,
                xp: r.xp_awarded,
                correctAnswer: r.correct_answer,
                note: r.completed ? t("challenge.bonus", { xp: r.bonus_xp }) : undefined,
              };
            }}
            finished={
              <>
                {bonus > 0 && <p>{t("challenge.bonus", { xp: bonus })}</p>}
                <Link to="/" className="mt-4 inline-block underline">
                  {t("common.toDashboard")}
                </Link>
              </>
            }
          />
        ))}
    </section>
  );
}

import { useTranslation } from "react-i18next";
import type { Dashboard } from "../../api/client";

export function LevelBar({ level }: { level: Dashboard["level"] }) {
  const { t } = useTranslation();
  return (
    <div className="mt-2">
      <p className="font-semibold">
        {t("dashboard.level")} {level.level} · {level.title}
      </p>
      <progress
        className="h-2 w-full"
        value={level.xp_into_level}
        max={level.xp_for_next_level}
        aria-label={t("dashboard.level")}
      />
      <p className="text-sm">
        {level.xp_into_level} / {level.xp_for_next_level} XP · {t("dashboard.totalXp", { xp: level.total_xp })}
      </p>
    </div>
  );
}

export function StreakText({ streak }: { streak: Dashboard["streak"] }) {
  const { t } = useTranslation();
  return (
    <div className="mt-2">
      <p className="font-semibold">{t("dashboard.streakDays", { count: streak.current })}</p>
      <p className="text-sm">
        {t("dashboard.freezes", { held: streak.freezes_held, max: streak.max_freezes })} ·{" "}
        {t("dashboard.longest", { count: streak.longest })}
      </p>
    </div>
  );
}

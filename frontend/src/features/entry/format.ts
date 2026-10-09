import type { TFunction } from "i18next";

/** Date display follows the certainty flag (scope 2.3). */
export function formatEventDate(
  date: string | null,
  certainty: string | undefined,
  t: TFunction,
): string {
  if (!date) return "";
  if (certainty === "approximate" || certainty === "estimated") {
    return `${t(`certainty.${certainty}`)} ${date.slice(0, 4)}`;
  }
  return new Date(`${date}T00:00:00`).toLocaleDateString("bg-BG", {
    day: "numeric",
    month: "long",
    year: "numeric",
  });
}

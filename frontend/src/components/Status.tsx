import type { UseQueryResult } from "@tanstack/react-query";
import { useTranslation } from "react-i18next";

/** Loading and error text for a query that has no data yet. Returns null once data exists. */
export default function QueryStatus({ query }: { query: UseQueryResult }) {
  const { t } = useTranslation();
  if (query.isPending) return <p>{t("common.loading")}</p>;
  if (query.isError) return <p role="alert">{t("common.error")}</p>;
  return null;
}

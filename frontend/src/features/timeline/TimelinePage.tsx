import { useQuery } from "@tanstack/react-query";
import { useState } from "react";
import { useTranslation } from "react-i18next";
import { api } from "../../api/client";
import QueryStatus from "../../components/Status";
import TimelineChart from "./TimelineChart";

export default function TimelinePage() {
  const { t } = useTranslation();
  const timeline = useQuery({ queryKey: ["timeline"], queryFn: api.timeline });
  const [selected, setSelected] = useState<string | null>(null);

  return (
    <section className="flex h-full min-h-0 flex-col">
      <h1 className="sr-only">{t("timeline.title")}</h1>
      <QueryStatus query={timeline} />
      {timeline.data && <TimelineChart timeline={timeline.data} selected={selected} onSelect={setSelected} />}
    </section>
  );
}

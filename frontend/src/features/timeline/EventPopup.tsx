import { useTranslation } from "react-i18next";
import { Link } from "react-router-dom";
import type { Timeline } from "../../api/client";
import { formatEventDate } from "../entry/format";

export const POPUP_WIDTH = 288;

type TimelineEvent = Timeline["events"][number];

interface Props {
  event: TimelineEvent;
  onClose: () => void;
}

/** Contents of the card shown next to a clicked dot. Locked events show only title and date. */
export default function EventPopup({ event, onClose }: Props) {
  const { t } = useTranslation();
  return (
    <>
      <button className="float-right text-sm underline" onClick={onClose} aria-label={t("timeline.close")}>
        ✕
      </button>
      <h2 className="font-serif text-xl">{event.title}</h2>
      <p className="text-sm">{formatEventDate(event.event_date, event.date_certainty, t)}</p>
      {event.locked ? (
        <p className="mt-3">🔒 {t("common.locked")}</p>
      ) : (
        <>
          <p className="mt-2 text-sm">{event.summary}</p>
          <Link
            to={`/entries/${event.slug}`}
            className="mt-3 block rounded bg-mocha px-4 py-2 text-center text-parchment"
          >
            {t("timeline.open")}
          </Link>
          {event.progress === "in_progress" ? (
            <Link
              to={`/entries/${event.slug}/quiz`}
              className="mt-2 block rounded border border-mocha px-4 py-2 text-center"
            >
              {t("timeline.quiz")}
            </Link>
          ) : (
            event.progress === null && (
              <button
                disabled
                title={t("timeline.quizHint")}
                className="mt-2 block w-full rounded border border-mocha px-4 py-2 opacity-40"
              >
                {t("timeline.quiz")}
              </button>
            )
          )}
        </>
      )}
    </>
  );
}

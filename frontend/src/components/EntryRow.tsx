import { useTranslation } from "react-i18next";
import { Link } from "react-router-dom";
import type { EntryListItem } from "../api/client";
import { formatEventDate } from "../features/entry/format";

/** One entry in a list. Locked entries show the title only and do not link (scope 3.4). */
export default function EntryRow({ entry }: { entry: EntryListItem }) {
  const { t } = useTranslation();
  const type = t(`entryType.${entry.type}`);
  if (entry.locked) {
    return (
      <li className="flex items-baseline gap-3 rounded border border-cappuccino/40 px-4 py-3 opacity-60">
        <span aria-hidden>🔒</span>
        <span className="font-serif text-lg">{entry.title}</span>
        <span className="ml-auto text-sm">{type}</span>
      </li>
    );
  }
  return (
    <li>
      <Link
        to={`/entries/${entry.slug}`}
        className="block rounded border border-cappuccino bg-white/40 px-4 py-3 hover:bg-white/70"
      >
        <div className="flex items-baseline gap-3">
          <span className="font-serif text-lg font-semibold">{entry.title}</span>
          <span className="ml-auto text-sm">{type}</span>
          {entry.progress && (
            <span className="rounded bg-cappuccino/40 px-2 text-xs">
              {t(`progress.${entry.progress}`)}
            </span>
          )}
        </div>
        {entry.event_date && (
          <div className="text-sm">{formatEventDate(entry.event_date, entry.date_certainty, t)}</div>
        )}
        {entry.summary && <p className="mt-1 text-sm">{entry.summary}</p>}
      </Link>
    </li>
  );
}

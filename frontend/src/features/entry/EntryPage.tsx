import { useTranslation } from "react-i18next";
import { Link, useParams } from "react-router-dom";
import type { EntryDetail } from "../../api/client";
import EntryMarkdown, { type EntryImage, type EntryLink } from "../../components/markdown/EntryMarkdown";
import QueryStatus from "../../components/Status";
import { formatEventDate } from "./format";
import { useEntry, useFinishedReading } from "./useEntries";

export default function EntryPage() {
  const { t } = useTranslation();
  const { slug } = useParams();
  const entry = useEntry(slug);

  if (!entry.data) return <QueryStatus query={entry} />;
  if (entry.data.locked) {
    return (
      <section>
        <h1 className="font-serif text-3xl">{entry.data.title}</h1>
        <p className="mt-2 font-semibold">🔒 {t("entry.lockedTitle")}</p>
        <p>{t("entry.lockedText")}</p>
        <Link to="/library" className="mt-4 inline-block underline">
          {t("entry.back")}
        </Link>
      </section>
    );
  }
  return <EntryView entry={entry.data} />;
}

function EntryView({ entry }: { entry: EntryDetail }) {
  const { t } = useTranslation();
  const finish = useFinishedReading(entry.slug);

  const links: Record<string, EntryLink> = Object.fromEntries(
    Object.entries(entry.links).map(([slug, link]) => [
      slug,
      { title: link.title, href: link.locked ? null : `/entries/${slug}` },
    ]),
  );
  const images: Record<string, EntryImage> = Object.fromEntries(
    entry.images.map((i) => [String(i.position), i]),
  );
  const mainImage = entry.images[0];
  const canTakeQuiz = entry.progress !== null;

  return (
    <div className="grid gap-8 lg:grid-cols-[1fr_16rem]">
      <article>
        <p className="text-sm">
          {t(`entryType.${entry.type}`)}
          {entry.progress && ` · ${t(`progress.${entry.progress}`)}`}
        </p>
        <h1 className="font-serif text-4xl">{entry.title}</h1>
        {entry.event_date && (
          <p className="mt-1">
            {formatEventDate(entry.event_date, entry.date_certainty, t)}
            {entry.date_note_old_style && ` (${t("entry.oldStyle")}: ${entry.date_note_old_style})`}
          </p>
        )}
        <p className="mt-1 text-sm">
          {[
            entry.region && `${t("entry.region")}: ${entry.region}`,
            entry.tracks.length > 0 && `${t("entry.tracks")}: ${entry.tracks.join(", ")}`,
            entry.phases.length > 0 && `${t("entry.phases")}: ${entry.phases.join(", ")}`,
          ]
            .filter(Boolean)
            .join(" · ")}
        </p>
        {mainImage && (
          <figure className="my-4">
            <img src={mainImage.src} alt={mainImage.caption} className="max-h-96 rounded" />
            <figcaption className="text-sm">
              {mainImage.caption}
              {mainImage.credit && ` (${mainImage.credit})`}
            </figcaption>
          </figure>
        )}
        <div className="entry-body my-6 font-serif text-lg leading-relaxed">
          <EntryMarkdown body={entry.body_md} links={links} images={images} />
        </div>
        {entry.sources.length > 0 && (
          <section className="mt-8 border-t border-cappuccino pt-4">
            <h2 className="font-serif text-xl">{t("entry.sources")}</h2>
            <ul className="list-disc pl-5">
              {entry.sources.map((s) => (
                <li key={s.citation}>
                  {s.url ? (
                    <a href={s.url} className="underline" target="_blank" rel="noreferrer">
                      {s.citation}
                    </a>
                  ) : (
                    s.citation
                  )}
                </li>
              ))}
            </ul>
          </section>
        )}
        <div className="mt-8 flex gap-3">
          {entry.progress === null && (
            <button
              onClick={() => finish.mutate()}
              disabled={finish.isPending}
              className="rounded bg-mocha px-5 py-2 text-parchment disabled:opacity-60"
            >
              {t("entry.finishedReading")}
            </button>
          )}
          {canTakeQuiz && (
            <Link
              to={`/entries/${entry.slug}/quiz`}
              className="rounded bg-mocha px-5 py-2 text-parchment"
            >
              {t("entry.startQuiz")}
            </Link>
          )}
        </div>
        {finish.isError && <p role="alert">{t("common.error")}</p>}
      </article>
      <aside>
        <h2 className="font-serif text-xl">{t("entry.related")}</h2>
        <ul className="mt-2 flex flex-col gap-1">
          {entry.related.map((r) => (
            <li key={r.id}>
              {r.locked ? (
                <span className="opacity-60">🔒 {r.title}</span>
              ) : (
                <Link to={`/entries/${r.slug}`} className="underline">
                  {r.title}
                </Link>
              )}
              <span className="ml-2 text-xs">{t(`entryType.${r.type}`)}</span>
            </li>
          ))}
        </ul>
      </aside>
    </div>
  );
}

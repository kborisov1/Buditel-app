import { useQuery } from "@tanstack/react-query";
import { useEffect, useState, type KeyboardEvent } from "react";
import { useTranslation } from "react-i18next";
import { useNavigate } from "react-router-dom";
import { api } from "../../api/client";

const MIN_QUERY = 2; // matches the backend (architecture 11)
const DEBOUNCE_MS = 250;
const MAX_SHOWN = 8;

/** Top-bar title search (scope 7): unlocked entries link, locked ones show the title only. */
export default function SearchBox() {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const [text, setText] = useState("");
  const [term, setTerm] = useState("");
  const [open, setOpen] = useState(false);
  const [active, setActive] = useState(-1);

  useEffect(() => {
    const timer = setTimeout(() => setTerm(text.trim()), DEBOUNCE_MS);
    return () => clearTimeout(timer);
  }, [text]);

  const enabled = term.length >= MIN_QUERY;
  const results = useQuery({
    queryKey: ["search", term],
    queryFn: () => api.search(term),
    enabled,
  });
  const items = (enabled ? (results.data ?? []) : []).slice(0, MAX_SHOWN);

  function close() {
    setOpen(false);
    setActive(-1);
  }

  function go(to: string) {
    navigate(to);
    setText("");
    setTerm("");
    close();
  }

  function onKeyDown(event: KeyboardEvent) {
    if (event.key === "Escape") return close();
    if (event.key === "ArrowDown" || event.key === "ArrowUp") {
      event.preventDefault();
      setOpen(true);
      const step = event.key === "ArrowDown" ? 1 : -1;
      setActive((i) => Math.min(items.length - 1, Math.max(-1, i + step)));
    }
  }

  function onSubmit(event: React.FormEvent) {
    event.preventDefault();
    const chosen = items[active];
    if (chosen && !chosen.locked) return go(`/entries/${chosen.slug}`);
    const q = text.trim();
    go(q ? `/library?q=${encodeURIComponent(q)}` : "/library");
  }

  const showList = open && enabled && term === text.trim() && !results.isPending;

  return (
    <form onSubmit={onSubmit} role="search" className="relative ml-auto">
      <input
        type="search"
        aria-label={t("nav.search")}
        placeholder={t("nav.searchPlaceholder")}
        value={text}
        onChange={(e) => {
          setText(e.target.value);
          setOpen(true);
          setActive(-1);
        }}
        onFocus={() => setOpen(true)}
        onBlur={close}
        onKeyDown={onKeyDown}
        className="w-56 rounded border border-cappuccino bg-white/60 px-3 py-1"
      />
      {showList && (
        <ul
          // Keeps the input focused so a click on a result is not lost to the blur.
          onMouseDown={(e) => e.preventDefault()}
          className="absolute right-0 z-20 mt-1 w-80 rounded border border-cappuccino bg-parchment shadow-lg"
        >
          {items.length === 0 && <li className="px-3 py-2 text-sm">{t("nav.searchNone")}</li>}
          {items.map((entry, i) => (
            <li key={entry.id}>
              {entry.locked ? (
                <span className="flex gap-2 px-3 py-2 opacity-60" aria-disabled>
                  🔒 {entry.title}
                  <span className="ml-auto text-xs">{t(`entryType.${entry.type}`)}</span>
                </span>
              ) : (
                <button
                  type="button"
                  onClick={() => go(`/entries/${entry.slug}`)}
                  className={`flex w-full gap-2 px-3 py-2 text-left ${i === active ? "bg-cappuccino/40" : "hover:bg-cappuccino/30"}`}
                >
                  {entry.title}
                  <span className="ml-auto text-xs">{t(`entryType.${entry.type}`)}</span>
                </button>
              )}
            </li>
          ))}
          <li className="border-t border-cappuccino/50">
            <button
              type="button"
              onClick={() => go(`/library?q=${encodeURIComponent(term)}`)}
              className="w-full px-3 py-2 text-left text-sm underline"
            >
              {t("nav.searchAll")}
            </button>
          </li>
        </ul>
      )}
    </form>
  );
}

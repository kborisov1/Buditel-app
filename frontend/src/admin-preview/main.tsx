import { useEffect, useState } from "react";
import { createRoot } from "react-dom/client";
import EntryMarkdown, { type EntryLink } from "../components/markdown/EntryMarkdown";

// Live preview for the Django admin Markdown widget (architecture 9).
// Built by `make admin-assets` into backend/apps/content/static/content/.

function LivePreview({ textarea, links }: { textarea: HTMLTextAreaElement; links: Record<string, EntryLink> }) {
  const [body, setBody] = useState(textarea.value);
  useEffect(() => {
    const update = () => setBody(textarea.value);
    textarea.addEventListener("input", update);
    return () => textarea.removeEventListener("input", update);
  }, [textarea]);
  return <EntryMarkdown body={body} links={links} />;
}

function mount() {
  document.querySelectorAll<HTMLElement>("[data-markdown-preview]").forEach((target) => {
    const textarea = document.getElementById(target.dataset.markdownPreview ?? "");
    const linksEl = document.getElementById(target.dataset.links ?? "");
    if (!(textarea instanceof HTMLTextAreaElement)) return;
    const links = linksEl ? (JSON.parse(linksEl.textContent ?? "{}") as Record<string, EntryLink>) : {};
    target.textContent = "";
    createRoot(target).render(<LivePreview textarea={textarea} links={links} />);
  });
}

if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", mount);
else mount();

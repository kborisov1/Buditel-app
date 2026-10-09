import { useEffect, useState } from "react";
import { createRoot } from "react-dom/client";
import EntryMarkdown, {
  type EntryImage,
  type EntryLink,
} from "../components/markdown/EntryMarkdown";

// Live preview for the Django admin Markdown widget (architecture 9).
// Built by `make admin-assets` into backend/apps/content/static/content/.

interface Refs {
  links: Record<string, EntryLink>;
  images: Record<string, EntryImage>;
}

function LivePreview({ textarea, refs }: { textarea: HTMLTextAreaElement; refs: Refs }) {
  const [body, setBody] = useState(textarea.value);
  useEffect(() => {
    const update = () => setBody(textarea.value);
    textarea.addEventListener("input", update);
    return () => textarea.removeEventListener("input", update);
  }, [textarea]);
  return <EntryMarkdown body={body} links={refs.links} images={refs.images} />;
}

function mount() {
  document.querySelectorAll<HTMLElement>("[data-markdown-preview]").forEach((target) => {
    const textarea = document.getElementById(target.dataset.markdownPreview ?? "");
    const refsEl = document.getElementById(target.dataset.refs ?? "");
    if (!(textarea instanceof HTMLTextAreaElement)) return;
    const refs: Refs = { links: {}, images: {}, ...JSON.parse(refsEl?.textContent || "{}") };
    target.textContent = "";
    createRoot(target).render(<LivePreview textarea={textarea} refs={refs} />);
  });
}

if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", mount);
else mount();

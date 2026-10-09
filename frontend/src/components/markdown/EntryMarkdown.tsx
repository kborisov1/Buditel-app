import Markdown, { type Components } from "react-markdown";
import remarkEntryLinks from "./remarkEntryLinks";

/** A resolved [[slug]] target. A null href means the target is locked: show the title only. */
export interface EntryLink {
  title: string;
  href: string | null;
}

interface Props {
  body: string;
  links: Record<string, EntryLink>;
}

/** Entry body renderer shared by the learner app and the admin preview (architecture 8). */
export default function EntryMarkdown({ body, links }: Props) {
  const components: Components = {
    span({ node, children, ...rest }) {
      const slug = node?.properties.dataEntrySlug;
      if (typeof slug !== "string") return <span {...rest}>{children}</span>;
      const label = node?.properties.dataEntryLabel;
      const target = links[slug];
      if (!target) return <span className="entry-link-missing">[[{slug}]]</span>;
      const text = typeof label === "string" && label ? label : target.title;
      if (target.href === null) return <span className="entry-link-locked">{text}</span>;
      return (
        <a className="entry-link" href={target.href}>
          {text}
        </a>
      );
    },
  };
  return (
    <Markdown remarkPlugins={[remarkEntryLinks]} components={components}>
      {body}
    </Markdown>
  );
}

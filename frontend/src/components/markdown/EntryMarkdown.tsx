import Markdown, { type Components } from "react-markdown";
import remarkEntryLinks from "./remarkEntryLinks";

/** A resolved [[slug]] target. A null href means the target is locked: show the title only. */
export interface EntryLink {
  title: string;
  href: string | null;
}

/** An entry image, referenced in the body as ![[position]]. */
export interface EntryImage {
  src: string;
  caption: string;
  credit: string;
}

interface Props {
  body: string;
  links: Record<string, EntryLink>;
  images?: Record<string, EntryImage>;
}

/** Entry body renderer shared by the learner app and the admin preview (architecture 8). */
export default function EntryMarkdown({ body, links, images = {} }: Props) {
  const components: Components = {
    span({ node, children, ...rest }) {
      const position = node?.properties.dataEntryImage;
      if (typeof position === "string") {
        const image = images[position];
        if (!image) return <span className="entry-image-missing">![[{position}]]</span>;
        return (
          <span className="entry-image">
            <img src={image.src} alt={image.caption} />
            <span className="entry-image-caption">
              {image.caption}
              {image.credit && <span className="entry-image-credit"> ({image.credit})</span>}
            </span>
          </span>
        );
      }
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

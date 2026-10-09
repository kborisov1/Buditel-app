import type { Parent, PhrasingContent, Root, RootContent, Text } from "mdast";

// [[slug]] or [[slug|label]] (architecture 8).
const LINK = /\[\[([^\]|]+?)(?:\|([^\]]+?))?\]\]/g;

function split(node: Text): PhrasingContent[] {
  const out: PhrasingContent[] = [];
  let last = 0;
  for (const match of node.value.matchAll(LINK)) {
    const start = match.index;
    if (start > last) out.push({ type: "text", value: node.value.slice(last, start) });
    const slug = match[1].trim();
    const label = match[2]?.trim() ?? "";
    out.push({
      type: "text",
      value: label || slug,
      data: { hName: "span", hProperties: { dataEntrySlug: slug, dataEntryLabel: label } },
    });
    last = start + match[0].length;
  }
  if (last === 0) return [node];
  if (last < node.value.length) out.push({ type: "text", value: node.value.slice(last) });
  return out;
}

function walk(parent: Parent): void {
  parent.children = parent.children.flatMap((child): RootContent[] => {
    if (child.type === "text") return split(child);
    if ("children" in child) walk(child);
    return [child];
  }) as Parent["children"];
}

/** Turns [[slug]] text into spans carrying data-entry-slug, rendered by EntryMarkdown. */
export default function remarkEntryLinks() {
  return (tree: Root) => walk(tree);
}

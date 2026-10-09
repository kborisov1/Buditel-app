import type { Parent, PhrasingContent, Root, RootContent, Text } from "mdast";

// ![[position]] image, or [[slug]] / [[slug|label]] link (architecture 8).
const REF = /!\[\[(\d+)\]\]|\[\[([^\]|]+?)(?:\|([^\]]+?))?\]\]/g;

function split(node: Text): PhrasingContent[] {
  const out: PhrasingContent[] = [];
  let last = 0;
  for (const match of node.value.matchAll(REF)) {
    const start = match.index;
    if (start > last) out.push({ type: "text", value: node.value.slice(last, start) });
    const [, position, slug, label] = match;
    if (position) {
      out.push({
        type: "text",
        value: "",
        data: { hName: "span", hProperties: { dataEntryImage: position } },
      });
    } else {
      out.push({
        type: "text",
        value: label?.trim() || slug.trim(),
        data: {
          hName: "span",
          hProperties: { dataEntrySlug: slug.trim(), dataEntryLabel: label?.trim() ?? "" },
        },
      });
    }
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

/** Turns [[slug]] and ![[position]] text into marked spans, rendered by EntryMarkdown. */
export default function remarkEntryLinks() {
  return (tree: Root) => walk(tree);
}

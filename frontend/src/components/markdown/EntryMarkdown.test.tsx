import { render } from "@testing-library/react";
import { expect, test } from "vitest";
import EntryMarkdown, { type EntryLink } from "./EntryMarkdown";

const links: Record<string, EntryLink> = {
  paisiy: { title: "Паисий Хилендарски", href: "/entries/1" },
  "april-uprising": { title: "Априлско въстание", href: null },
};

function html(body: string) {
  return render(<EntryMarkdown body={body} links={links} />).container.innerHTML;
}

test("renders Markdown", () => {
  expect(html("# Заглавие\n\n**удебелен**")).toContain("<strong>удебелен</strong>");
});

test("links an unlocked entry with its title", () => {
  expect(html("Виж [[paisiy]].")).toContain(
    '<a class="entry-link" href="/entries/1">Паисий Хилендарски</a>',
  );
});

test("uses a custom label", () => {
  expect(html("[[paisiy|Паисий]]")).toContain(">Паисий</a>");
});

test("shows a locked entry as plain title", () => {
  const out = html("[[april-uprising]]");
  expect(out).toContain('<span class="entry-link-locked">Априлско въстание</span>');
  expect(out).not.toContain("<a");
});

test("flags an unknown slug", () => {
  expect(html("[[nope]]")).toContain('<span class="entry-link-missing">[[nope]]</span>');
});

test("handles several links in one paragraph and inside emphasis", () => {
  const out = html("*[[paisiy]]* и [[april-uprising]] край");
  expect(out).toContain("<em><a");
  expect(out).toContain("entry-link-locked");
  expect(out).toContain(" край");
});

test("does not render raw HTML", () => {
  expect(html("<script>alert(1)</script>")).not.toContain("<script>");
});

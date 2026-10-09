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

const images = { "1": { src: "/media/entries/p.jpg", caption: "Паисий", credit: "Public domain" } };

test("renders an inline image with caption and credit", () => {
  const out = render(<EntryMarkdown body={"Текст ![[1]] край"} links={links} images={images} />)
    .container.innerHTML;
  expect(out).toContain('<img src="/media/entries/p.jpg" alt="Паисий">');
  expect(out).toContain("(Public domain)");
  expect(out).toContain(" край");
});

test("flags an unknown image position", () => {
  expect(html("![[3]]")).toContain('<span class="entry-image-missing">![[3]]</span>');
});

test("keeps an image and a link apart", () => {
  const out = render(<EntryMarkdown body={"![[1]] [[paisiy]]"} links={links} images={images} />)
    .container.innerHTML;
  expect(out).toContain("<img");
  expect(out).toContain('class="entry-link"');
});

import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { fireEvent, render, screen } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { afterEach, expect, test, vi } from "vitest";
import "../i18n";
import LibraryPage from "./library/LibraryPage";
import QuizPage from "./quiz/QuizPage";

function renderAt(path: string, element: React.ReactNode, route: string) {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={client}>
      <MemoryRouter initialEntries={[path]}>
        <Routes>
          <Route path={route} element={element} />
        </Routes>
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

afterEach(() => vi.unstubAllGlobals());

test("library shows locked entries as title only, without a link", async () => {
  const entries = [
    { locked: true, id: 1, slug: "a", type: "event", title: "Заключено събитие", event_date: null },
    {
      locked: false, id: 2, slug: "b", type: "person", title: "Отворена личност", summary: "Кратко",
      event_date: null, date_certainty: "exact", region: "", importance: "minor", progress: null,
    },
  ];
  vi.stubGlobal("fetch", vi.fn().mockResolvedValue(Response.json(entries)));
  renderAt("/library", <LibraryPage />, "/library");
  expect(await screen.findByText("Заключено събитие")).toBeTruthy();
  expect(screen.getAllByRole("link")).toHaveLength(1);
  expect(screen.getByRole("link", { name: /Отворена личност/ })).toBeTruthy();
});

test("quiz submits answers and shows the failed score only", async () => {
  const quiz = {
    attempt_id: 7,
    questions: [
      { id: 1, type: "true_false", prompt: "Твърдение 1" },
      { id: 2, type: "date_ordering", prompt: "Подредба", items: ["Б", "А"] },
    ],
  };
  const fetchMock = vi.fn().mockImplementation((url: string) =>
    Promise.resolve(
      Response.json(url.endsWith("/quiz") ? quiz : { passed: false, score: 1, total: 2 }),
    ),
  );
  vi.stubGlobal("fetch", fetchMock);
  renderAt("/entries/x/quiz", <QuizPage />, "/entries/:slug/quiz");

  const submit = await screen.findByRole("button", { name: "Предай" });
  expect((submit as HTMLButtonElement).disabled).toBe(true);
  fireEvent.click(screen.getByLabelText("Вярно"));
  fireEvent.click(screen.getByRole("button", { name: /Надолу: Б/ }));
  fireEvent.click(submit);

  expect(await screen.findByText("Не издържахте теста.")).toBeTruthy();
  const body = JSON.parse(fetchMock.mock.calls.at(-1)![1].body);
  expect(body.answers).toEqual([
    { question_id: 1, answer: true },
    { question_id: 2, answer: ["А", "Б"] },
  ]);
});

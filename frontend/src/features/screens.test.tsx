import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { afterEach, expect, test, vi } from "vitest";
import "../i18n";
import SearchBox from "../components/layout/SearchBox";
import LibraryPage from "./library/LibraryPage";
import QuestionStepper from "./quiz/QuestionStepper";
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

afterEach(() => {
  cleanup();
  vi.unstubAllGlobals();
});

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

test("stepper shows feedback after an answer and the entry link only when given", async () => {
  const questions = [{ id: 1, type: "true_false", prompt: "Въпрос" }];
  const answered = vi.fn().mockResolvedValue({
    correct: false,
    explanation: "Защото така.",
    xp: 0,
    entry: { slug: "e", title: "Записът" },
  });
  renderAt(
    "/",
    <QuestionStepper questions={questions} onAnswer={answered} finished={<p>край</p>} />,
    "/",
  );
  const answer = screen.getByRole("button", { name: "Отговори" });
  expect((answer as HTMLButtonElement).disabled).toBe(true);
  fireEvent.click(screen.getByLabelText("Вярно"));
  fireEvent.click(answer);
  expect(await screen.findByText("Защото така.")).toBeTruthy();
  expect(screen.getByRole("link", { name: /Записът/ })).toBeTruthy();
  fireEvent.click(screen.getByRole("button", { name: "Завърши" }));
  expect(await screen.findByText("край")).toBeTruthy();
});

test("library passes track, period and region filters to the API", async () => {
  const profile = { tracks: [{ id: 3, name: "Просвета", kind: "regular", read: 0, total: 2 }] };
  const timeline = { start: "1762-01-01", end: "1878-12-31", events: [], phases: [{ id: 5, name: "Пробуждане", start_date: "1762-01-01", end_date: "1820-12-31" }] };
  const fetchMock = vi.fn().mockImplementation((url: string) =>
    Promise.resolve(Response.json(url.includes("/profile") ? profile : url.includes("/timeline") ? timeline : [])),
  );
  vi.stubGlobal("fetch", fetchMock);
  renderAt("/library", <LibraryPage />, "/library");
  const track = await screen.findByLabelText("Пътека");
  await screen.findByRole("option", { name: "Просвета" });
  fireEvent.change(track, { target: { value: "3" } });
  await screen.findByRole("button", { name: "Изчисти филтрите" });
  const urls = fetchMock.mock.calls.map((c) => c[0] as string);
  expect(urls.some((u) => u.includes("/entries?") && u.includes("track=3"))).toBe(true);
});

test("search box lists matches, shows locked ones as plain titles, and links the rest", async () => {
  const results = [
    { locked: true, id: 1, slug: "a", type: "event", title: "Заключено въстание", event_date: null },
    { locked: false, id: 2, slug: "b", type: "event", title: "Априлско въстание", summary: "", event_date: null, date_certainty: "exact", region: "", importance: "major", progress: null },
  ];
  vi.stubGlobal("fetch", vi.fn().mockResolvedValue(Response.json(results)));
  renderAt("/", <SearchBox />, "/");
  fireEvent.change(screen.getByRole("searchbox"), { target: { value: "въст" } });
  expect(await screen.findByText(/Заключено въстание/)).toBeTruthy();
  expect(screen.getByRole("button", { name: /Априлско въстание/ })).toBeTruthy();
  expect(screen.queryByRole("button", { name: /Заключено/ })).toBeNull();
});

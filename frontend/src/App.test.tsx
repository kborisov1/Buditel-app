import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { afterEach, expect, test, vi } from "vitest";
import App from "./App";
import "./i18n";

function renderApp() {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={client}>
      <MemoryRouter>
        <App />
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

afterEach(() => vi.unstubAllGlobals());

test("shows the login form when not authenticated", async () => {
  vi.stubGlobal("fetch", vi.fn().mockResolvedValue(new Response(null, { status: 401 })));
  renderApp();
  expect(await screen.findByRole("button", { name: "Вход" })).toBeTruthy();
});

const dashboard = {
  goal: { target: 40, earned_today: 0, reached: false },
  streak: { current: 0, longest: 0, freezes_held: 0, max_freezes: 2 },
  level: { level: 1, title: "Селянин", total_xp: 0, xp_into_level: 0, xp_for_next_level: 100 },
  reviews_due: 0,
};

test("shows the user when authenticated", async () => {
  const user = { id: 1, email: "a@b.bg", time_zone: "UTC", is_admin: false };
  vi.stubGlobal(
    "fetch",
    vi.fn().mockImplementation((url: string) =>
      Promise.resolve(Response.json(url.endsWith("/auth/me") ? user : url.endsWith("/dashboard") ? dashboard : [])),
    ),
  );
  renderApp();
  expect(await screen.findByText("a@b.bg")).toBeTruthy();
});

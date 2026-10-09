import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen } from "@testing-library/react";
import { afterEach, expect, test, vi } from "vitest";
import App from "./App";
import "./i18n";

function renderApp() {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={client}>
      <App />
    </QueryClientProvider>,
  );
}

afterEach(() => vi.unstubAllGlobals());

test("shows the login form when not authenticated", async () => {
  vi.stubGlobal("fetch", vi.fn().mockResolvedValue(new Response(null, { status: 401 })));
  renderApp();
  expect(await screen.findByRole("button", { name: "Вход" })).toBeTruthy();
});

test("shows the user when authenticated", async () => {
  const user = { id: 1, email: "a@b.bg", time_zone: "UTC", is_admin: false };
  vi.stubGlobal("fetch", vi.fn().mockResolvedValue(Response.json(user)));
  renderApp();
  expect(await screen.findByText("a@b.bg")).toBeTruthy();
});

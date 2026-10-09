import { render, screen } from "@testing-library/react";
import { expect, test } from "vitest";
import App from "./App";
import "./i18n";

test("renders the app name from i18n", () => {
  render(<App />);
  expect(screen.getByRole("heading", { name: "Будител" })).toBeTruthy();
});

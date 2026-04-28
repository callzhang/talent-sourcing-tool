import "@testing-library/jest-dom/vitest";
import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, expect, it } from "vitest";

import { App } from "./App";

afterEach(() => {
  cleanup();
});

it("renders the app shell on the jobs tab", () => {
  render(<App />);

  expect(screen.getByRole("heading", { name: "Talent Sourcing Tool" })).toBeInTheDocument();
  expect(screen.getByRole("heading", { name: "JD Management" })).toBeInTheDocument();
  expect(screen.getByRole("button", { name: "Jobs" })).toHaveAttribute("aria-pressed", "true");
});

it("switches between shell tabs without routing dependencies", () => {
  render(<App />);

  fireEvent.click(screen.getByRole("button", { name: "Search" }));

  expect(screen.getByRole("heading", { name: "Search Runs" })).toBeInTheDocument();
  expect(screen.getByRole("button", { name: "Search" })).toHaveAttribute("aria-pressed", "true");
});

import "@testing-library/jest-dom/vitest";
import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, expect, it, vi } from "vitest";

import { SearchPage } from "./SearchPage";
import type { Candidate, Job } from "../types";

afterEach(() => {
  cleanup();
  vi.restoreAllMocks();
});

it("loads persisted runs and reports candidates from a new search", async () => {
  const onCandidatesFound = vi.fn();
  const fetchMock = vi.spyOn(globalThis, "fetch").mockImplementation(async (input, init) => {
    const url = String(input);
    const method = init?.method ?? "GET";
    if (url.endsWith("/api/search?job_id=job_1") && method === "GET") {
      return jsonResponse([
        {
          id: "search_run_old",
          job_id: "job_1",
          query: "existing ai pmm search",
          provider: "bright_data",
          status: "completed",
          params: { limit: 3 },
          candidate_count: 3,
          created_at: "2026-04-28T12:00:00Z",
          completed_at: "2026-04-28T12:01:00Z"
        }
      ]);
    }
    if (url.endsWith("/api/search") && method === "POST") {
      return jsonResponse({
        id: "search_run_new",
        status: "completed",
        candidates: [candidate]
      });
    }
    return jsonResponse([]);
  });

  render(
    <SearchPage
      jobs={[job]}
      selectedJobId="job_1"
      onSelectJob={() => undefined}
      onCandidatesFound={onCandidatesFound}
    />
  );

  expect(await screen.findByText("existing ai pmm search")).toBeInTheDocument();

  fireEvent.change(screen.getByLabelText("Search query"), {
    target: { value: "founding ai product engineer" }
  });
  fireEvent.change(screen.getByLabelText("Candidate limit"), {
    target: { value: "2" }
  });
  fireEvent.click(screen.getByRole("button", { name: "Create search run" }));

  await waitFor(() => expect(onCandidatesFound).toHaveBeenCalledWith([candidate]));
  expect(await screen.findByText("Search completed with 1 candidates.")).toBeInTheDocument();
  expect(screen.getByText("New Candidate")).toBeInTheDocument();
  expect(fetchMock).toHaveBeenCalledWith(
    "http://localhost:8000/api/search",
    expect.objectContaining({
      method: "POST",
      body: JSON.stringify({
        job_id: "job_1",
        query: "founding ai product engineer",
        params: { limit: 2 }
      })
    })
  );
});

const job: Job = {
  id: "job_1",
  title: "AI Product Engineer",
  description: "Build prototypes",
  target_profile_text: "",
  red_flags_text: "",
  search_notes: "",
  status: "draft",
  created_at: "2026-04-28T12:00:00Z",
  updated_at: "2026-04-28T12:00:00Z"
};

const candidate: Candidate = {
  id: "candidate_1",
  linkedin_url: "https://www.linkedin.com/in/new",
  name: "New Candidate",
  headline: "AI builder",
  location: "San Francisco",
  current_company: "PrototypeCo",
  profile_data: {},
  created_at: "2026-04-28T12:00:00Z",
  updated_at: "2026-04-28T12:00:00Z",
  last_search_query: "founding ai product engineer",
  last_search_rank: 1
};

function jsonResponse(body: unknown) {
  return Promise.resolve(
    new Response(JSON.stringify(body), {
      status: 200,
      headers: { "Content-Type": "application/json" }
    })
  );
}

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
  const onReviewCandidate = vi.fn();
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
          channels: ["linkedin", "github", "exa"],
          status: "completed",
          params: { limit: 3 },
          candidate_count: 3,
          created_at: "2026-04-28T12:00:00Z",
          completed_at: "2026-04-28T12:01:00Z"
        }
      ]);
    }
    if (url.endsWith("/api/search/search_run_old") && method === "GET") {
      return jsonResponse({
        id: "search_run_old",
        job_id: "job_1",
        query: "existing ai pmm search",
        provider: "bright_data",
        channels: ["linkedin", "github", "exa"],
        status: "completed",
        params: { limit: 3 },
        candidate_count: 1,
        created_at: "2026-04-28T12:00:00Z",
        completed_at: "2026-04-28T12:01:00Z",
        candidates: [persistedCandidate]
      });
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
      onReviewCandidate={onReviewCandidate}
    />
  );

  expect(await screen.findByText("existing ai pmm search")).toBeInTheDocument();
  expect(await screen.findByText("Persisted Candidate")).toBeInTheDocument();
  expect(screen.getAllByText("LinkedIn + GitHub + Exa")).toHaveLength(2);
  expect(screen.getByText("Searching Channels")).toBeInTheDocument();

  fireEvent.change(screen.getByLabelText("Candidate limit"), {
    target: { value: "2" }
  });
  fireEvent.submit(screen.getByLabelText("Search query").closest("form") as HTMLFormElement);

  await waitFor(() => expect(onCandidatesFound).toHaveBeenCalledWith([candidate]));
  expect(await screen.findByText("Search completed with 1 candidates.")).toBeInTheDocument();
  expect(screen.getByText("New Candidate")).toBeInTheDocument();
  fireEvent.click(screen.getByRole("button", { name: "Open Persisted Candidate" }));
  expect(onReviewCandidate).toHaveBeenCalledWith(persistedCandidate);
  expect(fetchMock).toHaveBeenCalledWith(
    "http://localhost:8000/api/search",
    expect.objectContaining({
      method: "POST",
      body: JSON.stringify({
        job_id: "job_1",
        query: "Search configured from the JD",
        channels: ["linkedin", "github", "exa"],
        params: { limit: 2 }
      })
    })
  );
});

it("requires a selected JD before searching", () => {
  render(
    <SearchPage
      jobs={[]}
      selectedJobId={null}
      onSelectJob={() => undefined}
      onCandidatesFound={() => undefined}
      onReviewCandidate={() => undefined}
    />
  );

  fireEvent.change(screen.getByLabelText("Search query"), {
    target: { value: "ai builders" }
  });
  fireEvent.submit(screen.getByLabelText("Search query").closest("form") as HTMLFormElement);

  expect(screen.getByText("Create or select a JD before searching.")).toBeInTheDocument();
});

it("shows the active search channels while a search is running", async () => {
  let resolveSearch: (value: Response) => void = () => undefined;
  vi.spyOn(globalThis, "fetch").mockImplementation(async (input, init) => {
    const url = String(input);
    const method = init?.method ?? "GET";
    if (url.endsWith("/api/search?job_id=job_1") && method === "GET") {
      return jsonResponse([]);
    }
    if (url.endsWith("/api/search") && method === "POST") {
      return new Promise<Response>((resolve) => {
        resolveSearch = resolve;
      });
    }
    return jsonResponse([]);
  });

  render(
    <SearchPage
      jobs={[job]}
      selectedJobId="job_1"
      onSelectJob={() => undefined}
      onCandidatesFound={() => undefined}
      onReviewCandidate={() => undefined}
    />
  );

  fireEvent.click(screen.getByRole("button", { name: "Create search run" }));
  expect(await screen.findByText("Running sourcing search on LinkedIn + GitHub + Exa...")).toBeInTheDocument();

  resolveSearch(
    await jsonResponse({
      id: "search_run_new",
      status: "completed",
      candidates: [candidate]
    })
  );
  expect(await screen.findByText("Search completed with 1 candidates.")).toBeInTheDocument();
});

it("shows search run load and create errors", async () => {
  vi.spyOn(globalThis, "fetch")
    .mockImplementationOnce(() => errorResponse("Unable to load search runs."))
    .mockImplementationOnce(() => errorResponse("Unable to create search run."));

  render(
    <SearchPage
      jobs={[job]}
      selectedJobId="job_1"
      onSelectJob={() => undefined}
      onCandidatesFound={() => undefined}
      onReviewCandidate={() => undefined}
    />
  );

  expect(await screen.findByText("GET /api/search?job_id=job_1 failed with 500: Unable to load search runs.")).toBeInTheDocument();

  fireEvent.change(screen.getByLabelText("Search query"), {
    target: { value: "ai builders" }
  });
  fireEvent.click(screen.getByRole("button", { name: "Create search run" }));

  expect(await screen.findByText("POST /api/search failed with 500: Unable to create search run.")).toBeInTheDocument();
});

it("selects a different JD from the search form", () => {
  const onSelectJob = vi.fn();

  render(
    <SearchPage
      jobs={[job, { ...job, id: "job_2", title: "Business Intern" }]}
      selectedJobId="job_1"
      onSelectJob={onSelectJob}
      onCandidatesFound={() => undefined}
      onReviewCandidate={() => undefined}
    />
  );

  fireEvent.change(screen.getByLabelText("JD"), {
    target: { value: "job_2" }
  });

  expect(onSelectJob).toHaveBeenCalledWith("job_2");
});

const job: Job = {
  id: "job_1",
  title: "AI Product Engineer",
  description: "Build prototypes",
  target_profile_text: "",
  red_flags_text: "",
  search_notes: "Search configured from the JD",
  search_channels: ["linkedin", "github", "exa"],
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

const persistedCandidate: Candidate = {
  ...candidate,
  id: "candidate_persisted",
  name: "Persisted Candidate",
  headline: "Founding PMM",
  current_company: "MarketCo"
};

function jsonResponse(body: unknown) {
  return Promise.resolve(
    new Response(JSON.stringify(body), {
      status: 200,
      headers: { "Content-Type": "application/json" }
    })
  );
}

function errorResponse(detail: string) {
  return Promise.resolve(
    new Response(JSON.stringify({ detail }), {
      status: 500,
      statusText: "Internal Server Error",
      headers: { "Content-Type": "application/json" }
    })
  );
}

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
          channels: ["linkedin", "github", "exa", "brightdata_discover"],
          status: "completed",
          params: { limit: 3, region: "San Francisco, CA" },
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
        channels: ["linkedin", "github", "exa", "brightdata_discover"],
        status: "completed",
        params: { limit: 3, region: "San Francisco, CA" },
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
      systemStatus={null}
      onSelectJob={() => undefined}
      onCandidatesFound={onCandidatesFound}
      onReviewCandidate={onReviewCandidate}
    />
  );

  expect(await screen.findByText("existing ai pmm search")).toBeInTheDocument();
  expect(await screen.findByText("Persisted Candidate")).toBeInTheDocument();
  expect(screen.getAllByText("LinkedIn + GitHub + Exa + Bright Data Discover")).toHaveLength(2);
  expect(screen.getAllByText("San Francisco, CA")).toHaveLength(2);
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
    "/api/search",
    expect.objectContaining({
      method: "POST",
      body: JSON.stringify({
        job_id: "job_1",
        query: "Search configured from the JD",
        channels: ["linkedin", "github", "exa", "brightdata_discover"],
        params: { limit: 2, region: "San Francisco, CA" }
      })
    })
  );
});

it("requires a selected JD before searching", () => {
  render(
    <SearchPage
      jobs={[]}
      selectedJobId={null}
      systemStatus={null}
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
      systemStatus={null}
      onSelectJob={() => undefined}
      onCandidatesFound={() => undefined}
      onReviewCandidate={() => undefined}
    />
  );

  fireEvent.click(screen.getByRole("button", { name: "Create search run" }));
  expect(
    await screen.findByText(
      "Running sourcing search on LinkedIn + GitHub + Exa + Bright Data Discover..."
    )
  ).toBeInTheDocument();

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
      systemStatus={null}
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
      systemStatus={null}
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

it("disables unavailable deployment channels and blocks search when production storage is incomplete", async () => {
  render(
    <SearchPage
      jobs={[job]}
      selectedJobId="job_1"
      systemStatus={{
        environment: "vercel",
        deployment_ready: false,
        warnings: [],
        capabilities: {
          persistent_storage_configured: false,
          review_provider: "openai",
          review_configured: false,
          linkedin_configured: false,
          exa_configured: false,
          brightdata_configured: false,
          public_channels: ["github", "openreview", "arxiv"],
          channel_availability: {
            linkedin: false,
            github: true,
            openreview: true,
            arxiv: true,
            exa: false,
            brightdata_discover: false
          },
          missing_env_vars: {
            storage: ["DATABASE_URL", "TALENT_DATABASE_URL"],
            review: ["TALENT_OPENAI_API_KEY"],
            channels: {
              linkedin: [
                "TALENT_EXA_API_KEY",
                "TALENT_BRIGHTDATA_API_KEY",
                "TALENT_BRIGHTDATA_ZONE"
              ],
              exa: ["TALENT_EXA_API_KEY"],
              brightdata_discover: ["TALENT_BRIGHTDATA_API_KEY", "TALENT_BRIGHTDATA_ZONE"]
            }
          }
        }
      }}
      onSelectJob={() => undefined}
      onCandidatesFound={() => undefined}
      onReviewCandidate={() => undefined}
    />
  );

  expect(await screen.findByDisplayValue("Search configured from the JD")).toBeInTheDocument();
  const linkedInChannel = screen.getByRole("checkbox", { name: /LinkedIn/ });
  expect(linkedInChannel).toBeDisabled();
  expect(linkedInChannel.closest("label")).toHaveClass("checkbox-row");
  expect(linkedInChannel.nextElementSibling).toHaveClass("channel-option-label");
  expect(screen.getAllByText("Unavailable")).toHaveLength(3);
  expect(screen.getByRole("checkbox", { name: /Exa/ })).toBeDisabled();
  expect(screen.getByRole("checkbox", { name: /Bright Data Discover/ })).toBeDisabled();
  expect(screen.getByRole("checkbox", { name: /GitHub/ })).toBeChecked();
  expect(screen.getByRole("button", { name: "Create search run" })).toBeDisabled();
  expect(
    screen.getByText("Search is blocked in production until durable database storage is configured.")
  ).toBeInTheDocument();
});

it("keeps LinkedIn available when Exa is configured even without Bright Data", async () => {
  render(
    <SearchPage
      jobs={[job]}
      selectedJobId="job_1"
      systemStatus={{
        environment: "vercel",
        deployment_ready: true,
        warnings: ["Optional production channel unavailable: Bright Data Discover."],
        capabilities: {
          persistent_storage_configured: true,
          review_provider: "openai",
          review_configured: true,
          linkedin_configured: true,
          exa_configured: true,
          brightdata_configured: false,
          public_channels: ["github", "openreview", "arxiv"],
          channel_availability: {
            linkedin: true,
            github: true,
            openreview: true,
            arxiv: true,
            exa: true,
            brightdata_discover: false
          },
          missing_env_vars: {
            storage: [],
            review: [],
            channels: {
              brightdata_discover: ["TALENT_BRIGHTDATA_API_KEY", "TALENT_BRIGHTDATA_ZONE"]
            }
          }
        }
      }}
      onSelectJob={() => undefined}
      onCandidatesFound={() => undefined}
      onReviewCandidate={() => undefined}
    />
  );

  expect(await screen.findByDisplayValue("Search configured from the JD")).toBeInTheDocument();
  expect(screen.getByRole("checkbox", { name: /LinkedIn/ })).toBeEnabled();
  expect(screen.getByRole("checkbox", { name: /Exa/ })).toBeEnabled();
  expect(screen.getByRole("checkbox", { name: /Bright Data Discover/ })).toBeDisabled();
});

const job: Job = {
  id: "job_1",
  title: "AI Product Engineer",
  description: "Build prototypes",
  region: "San Francisco, CA",
  target_profile_text: "",
  red_flags_text: "",
  search_notes: "Search configured from the JD",
  search_channels: ["linkedin", "github", "exa", "brightdata_discover"],
  created_at: "2026-04-28T12:00:00Z",
  updated_at: "2026-04-28T12:00:00Z"
};

const candidate: Candidate = {
  id: "candidate_1",
  profile_url: "https://www.linkedin.com/in/new",
  profile_source: "linkedin",
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

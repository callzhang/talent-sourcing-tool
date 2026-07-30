import "@testing-library/jest-dom/vitest";
import { cleanup, fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { afterEach, expect, it, vi } from "vitest";

import { CandidatesPage } from "./CandidatesPage";
import type { Candidate, Job } from "../types";

afterEach(() => {
  cleanup();
  vi.restoreAllMocks();
});

it("asks for a JD before loading candidates", () => {
  render(
    <CandidatesPage
      selectedJobId={null}
      jobs={[]}
      candidates={[]}
      systemStatus={null}
      onSelectJob={() => undefined}
      onLoadedCandidates={() => undefined}
      onReviewCandidate={() => undefined}
    />
  );

  expect(screen.getByText("Select a JD before reviewing candidates.")).toBeInTheDocument();
});

it("loads searched candidates and sends selected candidate to review", async () => {
  const onLoadedCandidates = vi.fn();
  const onReviewCandidate = vi.fn();
  vi.spyOn(globalThis, "fetch").mockImplementation(() => jsonResponse([candidate]));

  const { rerender } = render(
    <CandidatesPage
      selectedJobId="job_1"
      jobs={[job]}
      candidates={[]}
      systemStatus={null}
      onSelectJob={() => undefined}
      onLoadedCandidates={onLoadedCandidates}
      onReviewCandidate={onReviewCandidate}
    />
  );

  await waitFor(() => expect(onLoadedCandidates).toHaveBeenCalledWith([candidate]));

  rerender(
    <CandidatesPage
      selectedJobId="job_1"
      jobs={[job]}
      candidates={[candidate]}
      systemStatus={null}
      onSelectJob={() => undefined}
      onLoadedCandidates={onLoadedCandidates}
      onReviewCandidate={onReviewCandidate}
    />
  );

  const detailPane = screen.getByRole("region", { name: "Candidate detail" });
  expect(within(detailPane).getByText("Rank 2")).toBeInTheDocument();
  expect(within(detailPane).getByText("No headline captured")).toBeInTheDocument();
  expect(within(detailPane).getByText("LaunchCo · Remote")).toBeInTheDocument();

  fireEvent.click(screen.getByRole("button", { name: "Review Candidate One" }));
  expect(onReviewCandidate).toHaveBeenCalledWith(candidate);
});

it("renders candidate listings in the left pane and selected candidate details in the right pane", async () => {
  vi.spyOn(globalThis, "fetch").mockImplementation(() => jsonResponse([candidateWithEvidence]));

  render(
    <CandidatesPage
      selectedJobId="job_1"
      jobs={[job]}
      candidates={[candidateWithEvidence]}
      systemStatus={null}
      onSelectJob={() => undefined}
      onLoadedCandidates={() => undefined}
      onReviewCandidate={() => undefined}
    />
  );

  const queuePane = await screen.findByRole("region", { name: "Candidate listings" });
  const detailPane = await screen.findByRole("region", { name: "Candidate detail" });

  expect(queuePane).toContainElement(within(queuePane).getByRole("button", { name: /Candidate One/ }));
  expect(detailPane).toContainElement(screen.getByText("Evidence of structured PMF interviews."));
  expect(detailPane).toContainElement(screen.getByText("GitHub: Portfolio source"));
  expect(queuePane.compareDocumentPosition(detailPane) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy();
});

it("defaults to the job for the latest candidate when the selected JD has no candidates", async () => {
  const onSelectJob = vi.fn();
  vi.spyOn(globalThis, "fetch").mockImplementation(async (input) => {
    const url = String(input);
    if (url.endsWith("/api/candidates?job_id=job_1")) {
      return jsonResponse([]);
    }
    if (url.endsWith("/api/candidates")) {
      return jsonResponse([candidate]);
    }
    if (url.endsWith("/api/search/search_run_1")) {
      return jsonResponse(searchRunForPmmJob);
    }
    return jsonResponse([]);
  });

  render(
    <CandidatesPage
      selectedJobId="job_1"
      jobs={[job, pmmJob]}
      candidates={[]}
      systemStatus={null}
      onSelectJob={onSelectJob}
      onLoadedCandidates={() => undefined}
      onReviewCandidate={() => undefined}
    />
  );

  await waitFor(() => expect(onSelectJob).toHaveBeenCalledWith("job_pmm"));
});

it("renders empty and error states for candidate loading", async () => {
  const fetchMock = vi
    .spyOn(globalThis, "fetch")
    .mockImplementationOnce(() => jsonResponse([]))
    .mockImplementationOnce(() => errorResponse("Candidate API unavailable"));

  const { rerender } = render(
    <CandidatesPage
      selectedJobId="job_1"
      jobs={[job]}
      candidates={[]}
      systemStatus={null}
      onSelectJob={() => undefined}
      onLoadedCandidates={() => undefined}
      onReviewCandidate={() => undefined}
    />
  );

  expect(await screen.findByText("No searched candidates for this JD yet.")).toBeInTheDocument();

  rerender(
    <CandidatesPage
      selectedJobId="job_2"
      jobs={[job, pmmJob]}
      candidates={[]}
      systemStatus={null}
      onSelectJob={() => undefined}
      onLoadedCandidates={() => undefined}
      onReviewCandidate={() => undefined}
    />
  );

  expect(await screen.findByText("GET /api/candidates?job_id=job_2 failed with 500: Candidate API unavailable")).toBeInTheDocument();
  expect(fetchMock).toHaveBeenCalledTimes(2);
});

it("ignores candidate loads that resolve after unmount", async () => {
  let resolveCandidates: (response: Response) => void = () => undefined;
  vi.spyOn(globalThis, "fetch").mockImplementation(
    () =>
      new Promise<Response>((resolve) => {
        resolveCandidates = resolve;
      })
  );

  const onLoadedCandidates = vi.fn();
  const { unmount } = render(
    <CandidatesPage
      selectedJobId="job_1"
      jobs={[job]}
      candidates={[]}
      systemStatus={null}
      onSelectJob={() => undefined}
      onLoadedCandidates={onLoadedCandidates}
      onReviewCandidate={() => undefined}
    />
  );

  unmount();
  resolveCandidates(await jsonResponse([candidate]));
  expect(onLoadedCandidates).not.toHaveBeenCalled();
});

it("lets the user switch the JD used by the candidate queue", async () => {
  const onSelectJob = vi.fn();
  vi.spyOn(globalThis, "fetch").mockImplementation(() => jsonResponse([]));

  render(
    <CandidatesPage
      selectedJobId="job_1"
      jobs={[job, pmmJob]}
      candidates={[]}
      systemStatus={null}
      onSelectJob={onSelectJob}
      onLoadedCandidates={() => undefined}
      onReviewCandidate={() => undefined}
    />
  );

  fireEvent.change(screen.getByLabelText("Review queue JD"), {
    target: { value: "job_pmm" }
  });

  expect(onSelectJob).toHaveBeenCalledWith("job_pmm");
});

it("explains why the queue stays empty when production search is blocked by storage", async () => {
  vi.spyOn(globalThis, "fetch").mockImplementation(() => jsonResponse([]));

  render(
    <CandidatesPage
      selectedJobId="job_1"
      jobs={[job]}
      candidates={[]}
      systemStatus={{
        environment: "vercel",
        deployment_ready: false,
        warnings: [],
        capabilities: {
          persistent_storage_configured: false,
          review_provider: "openai",
          review_configured: false,
          exa_configured: false,
          brightdata_configured: false,
          public_channels: ["github", "openreview", "arxiv"]
        }
      }}
      onSelectJob={() => undefined}
      onLoadedCandidates={() => undefined}
      onReviewCandidate={() => undefined}
    />
  );

  expect(
    await screen.findByText(
      "Search is disabled in this deployment until durable database storage is configured."
    )
  ).toBeInTheDocument();
  expect(
    screen.getByText("Candidate review will stay empty in production until search can write durable data.")
  ).toBeInTheDocument();
});

const job: Job = {
  id: "job_1",
  title: "Business Intern",
  description: "Support sourcing",
  region: "",
  target_profile_text: "",
  red_flags_text: "",
  search_notes: "",
  search_channels: ["linkedin", "exa", "brightdata_discover"],
  created_at: "2026-04-28T12:00:00Z",
  updated_at: "2026-04-28T12:00:00Z"
};

const pmmJob: Job = {
  ...job,
  id: "job_pmm",
  title: "Founding PMM / PMF Discovery Lead",
  region: "San Francisco, CA"
};

const candidate: Candidate = {
  id: "candidate_1",
  profile_url: "https://www.linkedin.com/in/one",
  profile_source: "linkedin",
  name: "Candidate One",
  headline: null,
  location: "Remote",
  current_company: "LaunchCo",
  profile_data: {},
  created_at: "2026-04-28T12:00:00Z",
  updated_at: "2026-04-28T12:00:00Z",
  last_search_run_id: "search_run_1",
  last_search_rank: 2
};

const candidateWithEvidence: Candidate = {
  ...candidate,
  profile_data: {
    raw: {
      signals: ["Evidence of structured PMF interviews."],
      risks: ["Availability needs confirmation."],
      sources: [
        {
          source_type: "github",
          title: "Portfolio source",
          url: "https://example.com/profile",
          evidence: "Shows product discovery artifacts."
        }
      ]
    }
  }
};

const searchRunForPmmJob = {
  id: "search_run_1",
  job_id: "job_pmm",
  query: "Founding PMM",
  provider: "verified_public_web",
  status: "completed",
  params: {},
  candidate_count: 1,
  created_at: "2026-04-28T12:00:00Z",
  completed_at: "2026-04-28T12:00:00Z",
  candidates: [candidate]
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

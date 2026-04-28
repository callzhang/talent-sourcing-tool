import "@testing-library/jest-dom/vitest";
import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, expect, it, vi } from "vitest";

import { CandidatesPage } from "./CandidatesPage";
import type { Candidate } from "../types";

afterEach(() => {
  cleanup();
  vi.restoreAllMocks();
});

it("asks for a JD before loading candidates", () => {
  render(
    <CandidatesPage
      selectedJobId={null}
      candidates={[]}
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
      candidates={[]}
      onLoadedCandidates={onLoadedCandidates}
      onReviewCandidate={onReviewCandidate}
    />
  );

  await waitFor(() => expect(onLoadedCandidates).toHaveBeenCalledWith([candidate]));

  rerender(
    <CandidatesPage
      selectedJobId="job_1"
      candidates={[candidate]}
      onLoadedCandidates={onLoadedCandidates}
      onReviewCandidate={onReviewCandidate}
    />
  );

  expect(screen.getByText("Rank 2")).toBeInTheDocument();
  expect(screen.getByText("No headline captured")).toBeInTheDocument();
  expect(screen.getByText("LaunchCo · Remote")).toBeInTheDocument();

  fireEvent.click(screen.getByRole("button", { name: "Review Candidate One" }));
  expect(onReviewCandidate).toHaveBeenCalledWith(candidate);
});

it("renders empty and error states for candidate loading", async () => {
  const fetchMock = vi
    .spyOn(globalThis, "fetch")
    .mockImplementationOnce(() => jsonResponse([]))
    .mockImplementationOnce(() => errorResponse("Candidate API unavailable"));

  const { rerender } = render(
    <CandidatesPage
      selectedJobId="job_1"
      candidates={[]}
      onLoadedCandidates={() => undefined}
      onReviewCandidate={() => undefined}
    />
  );

  expect(await screen.findByText("No searched candidates for this JD yet.")).toBeInTheDocument();

  rerender(
    <CandidatesPage
      selectedJobId="job_2"
      candidates={[]}
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
      candidates={[]}
      onLoadedCandidates={onLoadedCandidates}
      onReviewCandidate={() => undefined}
    />
  );

  unmount();
  resolveCandidates(await jsonResponse([candidate]));
  expect(onLoadedCandidates).not.toHaveBeenCalled();
});

const candidate: Candidate = {
  id: "candidate_1",
  linkedin_url: "https://www.linkedin.com/in/one",
  name: "Candidate One",
  headline: null,
  location: "Remote",
  current_company: "LaunchCo",
  profile_data: {},
  created_at: "2026-04-28T12:00:00Z",
  updated_at: "2026-04-28T12:00:00Z",
  last_search_rank: 2
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

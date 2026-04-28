import "@testing-library/jest-dom/vitest";
import { cleanup, render, screen } from "@testing-library/react";
import { afterEach, expect, it, vi } from "vitest";

import { CandidateDetailPage } from "./CandidateDetailPage";
import type { Candidate } from "../types";

afterEach(() => {
  cleanup();
  vi.restoreAllMocks();
});

it("does not submit a stale candidate while the selected candidate is loading", async () => {
  const fetchMock = vi.spyOn(globalThis, "fetch").mockImplementation(async (input, init) => {
    const url = String(input);
    const method = init?.method ?? "GET";
    if (url.endsWith("/api/candidates/candidate_1?job_id=job_1")) {
      return jsonResponse(candidateOne);
    }
    if (url.endsWith("/api/reviews/latest?job_id=job_1&candidate_id=candidate_1")) {
      return jsonResponse(reviewOne);
    }
    if (url.endsWith("/api/candidates/candidate_2?job_id=job_1")) {
      return new Promise<Response>(() => undefined);
    }
    if (url.endsWith("/api/reviews/latest?job_id=job_1&candidate_id=candidate_2")) {
      return new Promise<Response>(() => undefined);
    }
    if (url.endsWith("/api/reviews/decision") && method === "POST") {
      return jsonResponse({ id: "decision_1" });
    }
    return jsonResponse(null);
  });

  const { rerender } = render(
    <CandidateDetailPage selectedJobId="job_1" candidate={candidateOne} onBack={() => undefined} />
  );

  expect(await screen.findByText("Loaded latest review.")).toBeInTheDocument();

  rerender(
    <CandidateDetailPage selectedJobId="job_1" candidate={candidateTwo} onBack={() => undefined} />
  );

  expect(screen.getByText("Loading candidate review context...")).toBeInTheDocument();
  expect(screen.queryByRole("button", { name: "Submit proceed" })).not.toBeInTheDocument();
  expect(fetchMock).not.toHaveBeenCalledWith(
    expect.stringContaining("/api/reviews/decision"),
    expect.anything()
  );
});

const candidateOne: Candidate = {
  id: "candidate_1",
  linkedin_url: "https://www.linkedin.com/in/one",
  name: "Candidate One",
  headline: "AI PMM",
  location: "Remote",
  current_company: "LaunchCo",
  profile_data: {},
  created_at: "2026-04-28T12:00:00Z",
  updated_at: "2026-04-28T12:00:00Z"
};

const candidateTwo: Candidate = {
  ...candidateOne,
  id: "candidate_2",
  linkedin_url: "https://www.linkedin.com/in/two",
  name: "Candidate Two"
};

const reviewOne = {
  id: "review_1",
  review_job_id: "review_job_1",
  job_id: "job_1",
  candidate_id: "candidate_1",
  summary: "Candidate one summary.",
  evidence: [],
  recommendation: "proceed",
  score: 8,
  review: {
    decision_summary: "Candidate one summary.",
    recommendation: "proceed",
    overall_score: 8
  },
  created_at: "2026-04-28T12:00:00Z"
};

function jsonResponse(body: unknown) {
  return Promise.resolve(
    new Response(JSON.stringify(body), {
      status: 200,
      headers: { "Content-Type": "application/json" }
    })
  );
}

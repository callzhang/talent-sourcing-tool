import "@testing-library/jest-dom/vitest";
import { act, cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
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

it("ignores a stale in-flight review result after the candidate changes", async () => {
  let resolveStaleReview: (response: Response) => void = () => undefined;
  const decisionPayloads: unknown[] = [];
  vi.spyOn(globalThis, "fetch").mockImplementation(async (input, init) => {
    const url = String(input);
    const method = init?.method ?? "GET";
    if (url.endsWith("/api/candidates/candidate_1?job_id=job_1")) {
      return jsonResponse(candidateOne);
    }
    if (url.endsWith("/api/reviews/latest?job_id=job_1&candidate_id=candidate_1")) {
      return jsonResponse(null);
    }
    if (url.endsWith("/api/candidates/candidate_2?job_id=job_1")) {
      return jsonResponse(candidateTwo);
    }
    if (url.endsWith("/api/reviews/latest?job_id=job_1&candidate_id=candidate_2")) {
      return jsonResponse(null);
    }
    if (url.endsWith("/api/reviews/start") && method === "POST") {
      return new Promise<Response>((resolve) => {
        resolveStaleReview = resolve;
      });
    }
    if (url.endsWith("/api/reviews/decision") && method === "POST") {
      decisionPayloads.push(JSON.parse(String(init?.body)));
      return jsonResponse({ id: "decision_1" });
    }
    return jsonResponse(null);
  });

  const { rerender } = render(
    <CandidateDetailPage selectedJobId="job_1" candidate={candidateOne} onBack={() => undefined} />
  );

  expect(await screen.findByText("Ready for AI review.")).toBeInTheDocument();
  fireEvent.click(screen.getByRole("button", { name: "Start AI review" }));
  expect(await screen.findByText("Running AI review...")).toBeInTheDocument();

  rerender(
    <CandidateDetailPage selectedJobId="job_1" candidate={candidateTwo} onBack={() => undefined} />
  );

  expect(await screen.findByRole("heading", { name: "Candidate Two" })).toBeInTheDocument();

  await act(async () => {
    resolveStaleReview(await jsonResponse(startReviewOne));
  });

  expect(screen.queryByText("Candidate one review summary.")).not.toBeInTheDocument();
  expect(screen.getByText("Start an AI review to see score, recommendation, and evidence.")).toBeInTheDocument();
  expect(screen.getByRole("button", { name: "Draft pass reason" })).toBeDisabled();

  fireEvent.click(screen.getByRole("button", { name: "Submit proceed" }));

  await waitFor(() => expect(decisionPayloads).toHaveLength(1));
  expect(decisionPayloads[0]).toEqual({
    job_id: "job_1",
    candidate_id: "candidate_2",
    decision: "proceed",
    notes: "",
    pass_reason_code: "manual_pass"
  });
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

const startReviewOne = {
  review_job_id: "review_job_1",
  review_id: "review_1",
  review: {
    candidate_id: "candidate_1",
    job_id: "job_1",
    decision_summary: "Candidate one review summary.",
    recommendation: "proceed",
    overall_score: 8
  }
};

function jsonResponse(body: unknown) {
  return Promise.resolve(
    new Response(JSON.stringify(body), {
      status: 200,
      headers: { "Content-Type": "application/json" }
    })
  );
}

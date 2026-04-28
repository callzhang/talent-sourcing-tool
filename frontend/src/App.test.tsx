import "@testing-library/jest-dom/vitest";
import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, expect, it, vi } from "vitest";

import { App } from "./App";

afterEach(() => {
  cleanup();
  vi.restoreAllMocks();
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

it("creates a job, displays its rubric, and uses it for search and candidates", async () => {
  vi.spyOn(globalThis, "fetch").mockImplementation(async (input, init) => {
    const url = String(input);
    const method = init?.method ?? "GET";
    if (url.endsWith("/api/jobs") && method === "GET") {
      return jsonResponse([]);
    }
    if (url.endsWith("/api/jobs") && method === "POST") {
      return jsonResponse(jobWithRubric);
    }
    if (url.endsWith("/api/search?job_id=job_1")) {
      return jsonResponse([]);
    }
    if (url.endsWith("/api/search") && method === "POST") {
      return jsonResponse(searchRunResult);
    }
    if (url.endsWith("/api/candidates?job_id=job_1")) {
      return jsonResponse(searchRunResult.candidates);
    }
    return jsonResponse(null);
  });

  render(<App />);

  fireEvent.change(await screen.findByLabelText("JD title"), {
    target: { value: "Founding PMM" }
  });
  fireEvent.change(screen.getByLabelText("JD description"), {
    target: { value: "Own positioning for AI launch." }
  });
  fireEvent.click(screen.getByRole("button", { name: "Create JD and rubric" }));

  expect(await screen.findByText("Founder-market judgment")).toBeInTheDocument();

  fireEvent.click(screen.getByRole("button", { name: "Search" }));
  fireEvent.change(await screen.findByLabelText("Search query"), {
    target: { value: "AI product marketer" }
  });
  fireEvent.click(screen.getByRole("button", { name: "Create search run" }));

  expect(await screen.findByText("Searched Candidate")).toBeInTheDocument();
});

it("starts review, drafts a pass reason, and submits pass feedback", async () => {
  vi.spyOn(globalThis, "fetch").mockImplementation(async (input, init) => {
    const url = String(input);
    const method = init?.method ?? "GET";
    if (url.endsWith("/api/jobs") && method === "GET") {
      return jsonResponse([jobWithRubric.job]);
    }
    if (url.endsWith("/api/jobs/job_1")) {
      return jsonResponse(jobWithRubric);
    }
    if (url.endsWith("/api/candidates?job_id=job_1")) {
      return jsonResponse(searchRunResult.candidates);
    }
    if (url.endsWith("/api/candidates/candidate_1?job_id=job_1")) {
      return jsonResponse(searchRunResult.candidates[0]);
    }
    if (url.endsWith("/api/reviews/latest?job_id=job_1&candidate_id=candidate_1")) {
      return jsonResponse(null);
    }
    if (url.endsWith("/api/reviews/start") && method === "POST") {
      return jsonResponse(reviewStart);
    }
    if (url.endsWith("/api/reviews/review_1/draft-pass-reason")) {
      return jsonResponse(draftPassReason);
    }
    if (url.endsWith("/api/reviews/decision") && method === "POST") {
      return jsonResponse(candidateDecision);
    }
    return jsonResponse([]);
  });

  render(<App />);

  fireEvent.click(await screen.findByRole("button", { name: "Candidates" }));
  fireEvent.click(await screen.findByRole("button", { name: "Review Searched Candidate" }));
  fireEvent.click(await screen.findByRole("button", { name: "Start AI review" }));

  expect(await screen.findByText("Weak public launch evidence.")).toBeInTheDocument();

  fireEvent.click(screen.getByRole("button", { name: "Draft pass reason" }));
  expect(await screen.findByDisplayValue("Insufficient public evidence.")).toBeInTheDocument();

  fireEvent.change(screen.getByLabelText("Decision notes and feedback"), {
    target: { value: "Need stronger launch artifacts." }
  });
  fireEvent.click(screen.getByRole("button", { name: "Submit pass" }));

  expect(await screen.findByText("Saved pass decision.")).toBeInTheDocument();
});

const jobWithRubric = {
  job: {
    id: "job_1",
    title: "Founding PMM",
    description: "Own positioning for AI launch.",
    target_profile_text: "",
    red_flags_text: "",
    search_notes: "",
    status: "draft",
    created_at: "2026-04-28T12:00:00Z",
    updated_at: "2026-04-28T12:00:00Z"
  },
  rubric: {
    id: "rubric_1",
    job_id: "job_1",
    version: 1,
    source_hash: "hash",
    rubric: {
      dimensions: [{ name: "Founder-market judgment", weight: 50 }]
    },
    created_at: "2026-04-28T12:00:00Z",
    updated_at: "2026-04-28T12:00:00Z"
  }
};

const searchRunResult = {
  id: "search_run_1",
  status: "completed",
  candidates: [
    {
      id: "candidate_1",
      linkedin_url: "https://www.linkedin.com/in/searched",
      name: "Searched Candidate",
      headline: "AI PMM",
      location: "Remote",
      current_company: "LaunchCo",
      profile_data: {},
      created_at: "2026-04-28T12:00:00Z",
      updated_at: "2026-04-28T12:00:00Z",
      last_search_query: "AI product marketer",
      last_search_rank: 1
    }
  ]
};

const reviewStart = {
  review_job_id: "review_job_1",
  review_id: "review_1",
  review: {
    overall_score: 42,
    recommendation: "pass",
    decision_summary: "Weak public launch evidence.",
    evidence: [{ label: "LinkedIn", detail: "No clear AI launch ownership." }]
  }
};

const draftPassReason = {
  reason_code: "insufficient_public_evidence",
  reason_text: "Insufficient public evidence.",
  evidence: ["No clear AI launch ownership."]
};

const candidateDecision = {
  id: "decision_1",
  job_id: "job_1",
  candidate_id: "candidate_1",
  review_id: "review_1",
  decision: "pass",
  notes: "Need stronger launch artifacts.",
  decided_by: "agent"
};

function jsonResponse(body: unknown) {
  return Promise.resolve(
    new Response(JSON.stringify(body), {
      status: 200,
      headers: { "Content-Type": "application/json" }
    })
  );
}

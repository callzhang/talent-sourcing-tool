import "@testing-library/jest-dom/vitest";
import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, expect, it, vi } from "vitest";

import { RefinementsPage } from "./RefinementsPage";
import type { Job } from "../types";

afterEach(() => {
  cleanup();
  vi.restoreAllMocks();
});

it("renders persisted refinement suggestions with reason-code metadata", async () => {
  vi.spyOn(globalThis, "fetch").mockResolvedValue(
    new Response(
      JSON.stringify([
        {
          id: "refinement_1",
          job_id: "job_1",
          pass_reason_id: "pass_reason_1",
          suggestion_type: "query_rewrite",
          suggestion_text: "Search for AI prototype builders with public launch evidence.",
          status: "pending",
          suggestion_metadata: {
            reason_codes: ["insufficient_public_evidence", "weak_builder_evidence"]
          },
          created_at: "2026-04-28T12:00:00Z",
          applied_at: null
        }
      ]),
      {
        status: 200,
        headers: { "Content-Type": "application/json" }
      }
    )
  );

  render(
    <RefinementsPage
      jobs={[job]}
      selectedJobId="job_1"
      onSelectJob={() => undefined}
    />
  );

  expect(await screen.findByText("Persisted suggestions from pass reasons.")).toBeInTheDocument();
  expect(
    screen.getByText("Search for AI prototype builders with public launch evidence.")
  ).toBeInTheDocument();
  expect(
    screen.getByText("insufficient_public_evidence, weak_builder_evidence")
  ).toBeInTheDocument();
});

it("handles no selected JD, empty results, and load errors", async () => {
  const fetchMock = vi
    .spyOn(globalThis, "fetch")
    .mockImplementationOnce(() => jsonResponse([]))
    .mockImplementationOnce(() => errorResponse("Refinement API unavailable"));

  const { rerender } = render(
    <RefinementsPage
      jobs={[job]}
      selectedJobId={null}
      onSelectJob={() => undefined}
    />
  );

  expect(screen.getByText("Select a JD to inspect persisted refinements.")).toBeInTheDocument();
  expect(fetchMock).not.toHaveBeenCalled();

  rerender(
    <RefinementsPage
      jobs={[job]}
      selectedJobId="job_1"
      onSelectJob={() => undefined}
    />
  );
  expect(await screen.findByText("No refinement suggestions yet.")).toBeInTheDocument();
  expect(
    screen.getByText("Pass a candidate with a reason to generate a refinement suggestion.")
  ).toBeInTheDocument();

  rerender(
    <RefinementsPage
      jobs={[job]}
      selectedJobId="job_2"
      onSelectJob={() => undefined}
    />
  );
  expect(await screen.findByText("GET /api/reviews/refinements?job_id=job_2 failed with 500: Refinement API unavailable")).toBeInTheDocument();
});

it("keeps refinement metadata rendering safe when reason codes are missing", async () => {
  vi.spyOn(globalThis, "fetch").mockResolvedValue(
    new Response(
      JSON.stringify([
        {
          id: "refinement_2",
          job_id: "job_1",
          pass_reason_id: null,
          suggestion_type: "rubric_adjustment",
          suggestion_text: "Clarify required portfolio evidence.",
          status: "pending",
          suggestion_metadata: {},
          created_at: "2026-04-28T12:00:00Z",
          applied_at: null
        }
      ]),
      {
        status: 200,
        headers: { "Content-Type": "application/json" }
      }
    )
  );

  render(
    <RefinementsPage
      jobs={[job]}
      selectedJobId="job_1"
      onSelectJob={() => undefined}
    />
  );

  expect(await screen.findByText("Clarify required portfolio evidence.")).toBeInTheDocument();
  expect(screen.getByText("No reason code metadata")).toBeInTheDocument();
});

it("selects a different JD from the refinement filter", () => {
  const onSelectJob = vi.fn();

  render(
    <RefinementsPage
      jobs={[job, { ...job, id: "job_2", title: "Business Intern" }]}
      selectedJobId="job_1"
      onSelectJob={onSelectJob}
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
  region: "",
  target_profile_text: "",
  red_flags_text: "",
  search_notes: "",
  search_channels: ["linkedin", "github", "exa", "brightdata_discover"],
  created_at: "2026-04-28T12:00:00Z",
  updated_at: "2026-04-28T12:00:00Z"
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

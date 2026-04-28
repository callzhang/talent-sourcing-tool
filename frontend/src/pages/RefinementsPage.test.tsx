import "@testing-library/jest-dom/vitest";
import { cleanup, render, screen } from "@testing-library/react";
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

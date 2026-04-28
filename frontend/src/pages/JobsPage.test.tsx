import "@testing-library/jest-dom/vitest";
import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, expect, it, vi } from "vitest";

import { JobsPage } from "./JobsPage";

afterEach(() => {
  cleanup();
  vi.restoreAllMocks();
});

it("loads existing jobs, selects the first one, and renders rubric details", async () => {
  const onSelectJob = vi.fn();
  vi.spyOn(globalThis, "fetch").mockImplementation(async (input) => {
    const url = String(input);
    if (url.endsWith("/api/jobs")) {
      return jsonResponse([job]);
    }
    if (url.endsWith("/api/jobs/job_1")) {
      return jsonResponse(jobWithRubric);
    }
    return jsonResponse(null);
  });

  const { rerender } = render(
    <JobsPage
      selectedJobId={null}
      onSelectJob={onSelectJob}
      onCreatedJob={() => undefined}
    />
  );

  await waitFor(() => expect(onSelectJob).toHaveBeenCalledWith("job_1"));
  rerender(
    <JobsPage
      selectedJobId="job_1"
      onSelectJob={onSelectJob}
      onCreatedJob={() => undefined}
    />
  );
  expect(await screen.findByText("Founder-market judgment")).toBeInTheDocument();
  expect(screen.getByText("45%")).toBeInTheDocument();
  expect(screen.getByText("Assess PMF discovery depth.")).toBeInTheDocument();
});

it("shows the selected JD details and rubric evidence fields", async () => {
  const onSelectJob = vi.fn();
  vi.spyOn(globalThis, "fetch").mockImplementation(async (input) => {
    const url = String(input);
    if (url.endsWith("/api/jobs")) {
      return jsonResponse([jobWithDetails]);
    }
    if (url.endsWith("/api/jobs/job_1")) {
      return jsonResponse(jobWithEvidenceRubric);
    }
    return jsonResponse(null);
  });

  render(
    <JobsPage
      selectedJobId="job_1"
      onSelectJob={onSelectJob}
      onCreatedJob={() => undefined}
    />
  );

  expect(await screen.findByText("Build customer demos.")).toBeInTheDocument();
  expect(screen.getByText("AI-native builder")).toBeInTheDocument();
  expect(screen.getByText("No shipping evidence")).toBeInTheDocument();
  expect(screen.getByText("Search for prototype builders")).toBeInTheDocument();
  expect(screen.getByText("Matches the role context, domain, and target profile.")).toBeInTheDocument();
  expect(screen.getByText("Evidence of customer-facing prototypes.")).toBeInTheDocument();
  expect(screen.getByText("Only internal tooling.")).toBeInTheDocument();
});

it("creates a job, forwards it to the app shell, and clears the form", async () => {
  const onCreatedJob = vi.fn();
  vi.spyOn(globalThis, "fetch").mockImplementation(async (input, init) => {
    const url = String(input);
    const method = init?.method ?? "GET";
    if (url.endsWith("/api/jobs") && method === "GET") {
      return jsonResponse([]);
    }
    if (url.endsWith("/api/jobs") && method === "POST") {
      return jsonResponse(jobWithRubric);
    }
    return jsonResponse(null);
  });

  render(
    <JobsPage
      selectedJobId={null}
      onSelectJob={() => undefined}
      onCreatedJob={onCreatedJob}
    />
  );

  fireEvent.change(await screen.findByLabelText("JD title"), {
    target: { value: "AI Product Engineer" }
  });
  fireEvent.change(screen.getByLabelText("JD description"), {
    target: { value: "Build customer demos." }
  });
  fireEvent.change(screen.getByLabelText("Target profile"), {
    target: { value: "AI-native builder" }
  });
  fireEvent.change(screen.getByLabelText("Red flags"), {
    target: { value: "No shipping evidence" }
  });
  fireEvent.change(screen.getByLabelText("Search notes"), {
    target: { value: "Search for prototype builders" }
  });
  fireEvent.click(screen.getByRole("button", { name: "Create JD and rubric" }));

  expect(await screen.findByText("JD created and rubric generated.")).toBeInTheDocument();
  expect(onCreatedJob).toHaveBeenCalledWith(jobWithRubric);
  expect(screen.getByLabelText("JD title")).toHaveValue("");
  expect(screen.getByText("Founder-market judgment")).toBeInTheDocument();
});

it("shows API errors from loading and creating jobs", async () => {
  vi.spyOn(globalThis, "fetch")
    .mockImplementationOnce(() => errorResponse("Unable to load jobs."))
    .mockImplementationOnce(() => errorResponse("Unable to create JD."));

  render(
    <JobsPage
      selectedJobId={null}
      onSelectJob={() => undefined}
      onCreatedJob={() => undefined}
    />
  );

  expect(await screen.findByText("GET /api/jobs failed with 500: Unable to load jobs.")).toBeInTheDocument();

  fireEvent.change(screen.getByLabelText("JD title"), {
    target: { value: "Broken JD" }
  });
  fireEvent.change(screen.getByLabelText("JD description"), {
    target: { value: "Broken description" }
  });
  fireEvent.click(screen.getByRole("button", { name: "Create JD and rubric" }));

  expect(await screen.findByText("POST /api/jobs failed with 500: Unable to create JD.")).toBeInTheDocument();
});

it("shows get-job errors when the active rubric cannot load", async () => {
  vi.spyOn(globalThis, "fetch").mockImplementation(async (input) => {
    const url = String(input);
    if (url.endsWith("/api/jobs")) {
      return jsonResponse([job]);
    }
    if (url.endsWith("/api/jobs/job_1")) {
      return errorResponse("Unable to load rubric.");
    }
    return jsonResponse(null);
  });

  render(
    <JobsPage
      selectedJobId="job_1"
      onSelectJob={() => undefined}
      onCreatedJob={() => undefined}
    />
  );

  expect(await screen.findByText("GET /api/jobs/job_1 failed with 500: Unable to load rubric.")).toBeInTheDocument();
});

it("selects a listed job when the user clicks it", async () => {
  const onSelectJob = vi.fn();
  vi.spyOn(globalThis, "fetch").mockImplementation(async (input) => {
    const url = String(input);
    if (url.endsWith("/api/jobs")) {
      return jsonResponse([job]);
    }
    return jsonResponse(jobWithRubric);
  });

  render(
    <JobsPage
      selectedJobId="job_other"
      onSelectJob={onSelectJob}
      onCreatedJob={() => undefined}
    />
  );

  fireEvent.click(await screen.findByRole("button", { name: /AI Product Engineer/ }));
  expect(onSelectJob).toHaveBeenCalledWith("job_1");
});

const job = {
  id: "job_1",
  title: "AI Product Engineer",
  description: "Build customer demos.",
  target_profile_text: "",
  red_flags_text: "",
  search_notes: "",
  status: "draft",
  created_at: "2026-04-28T12:00:00Z",
  updated_at: "2026-04-28T12:00:00Z"
};

const jobWithDetails = {
  ...job,
  target_profile_text: "AI-native builder",
  red_flags_text: "No shipping evidence",
  search_notes: "Search for prototype builders"
};

const jobWithRubric = {
  job,
  rubric: {
    id: "rubric_1",
    job_id: "job_1",
    version: 1,
    source_hash: "hash",
    rubric: {
      dimensions: [
        {
          name: "Founder-market judgment",
          weight: 45,
          scoring_guidance: "Assess PMF discovery depth."
        }
      ]
    },
    created_at: "2026-04-28T12:00:00Z",
    updated_at: "2026-04-28T12:00:00Z"
  }
};

const jobWithEvidenceRubric = {
  job: jobWithDetails,
  rubric: {
    id: "rubric_2",
    job_id: "job_1",
    version: 1,
    source_hash: "hash_2",
    rubric: {
      dimensions: [
        {
          name: "Role Fit",
          description: "Matches the role context, domain, and target profile.",
          signals: ["Evidence of customer-facing prototypes."],
          red_flags: ["Only internal tooling."]
        }
      ]
    },
    created_at: "2026-04-28T12:00:00Z",
    updated_at: "2026-04-28T12:00:00Z"
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

function errorResponse(detail: string) {
  return Promise.resolve(
    new Response(JSON.stringify({ detail }), {
      status: 500,
      statusText: "Internal Server Error",
      headers: { "Content-Type": "application/json" }
    })
  );
}

import "@testing-library/jest-dom/vitest";
import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, expect, it, vi } from "vitest";

import { App } from "./App";

afterEach(() => {
  cleanup();
  vi.restoreAllMocks();
});

it("renders the app shell on the jobs tab", () => {
  vi.spyOn(globalThis, "fetch").mockImplementation(async (input) => {
    const url = String(input);
    if (url.endsWith("/api/system/status")) {
      return jsonResponse({
        environment: "local",
        deployment_ready: true,
        warnings: [],
        capabilities: {
          persistent_storage_configured: true,
          review_provider: "codex",
          review_configured: true,
          linkedin_configured: true,
          exa_configured: true,
          brightdata_configured: true,
          public_channels: ["github", "openreview", "arxiv"],
          required_channels: ["linkedin", "github", "openreview", "arxiv", "exa"],
          optional_channels: ["brightdata_discover"],
          channel_availability: {
            linkedin: true,
            github: true,
            openreview: true,
            arxiv: true,
            exa: true,
            brightdata_discover: true
          },
          missing_env_vars: {
            storage: [],
            review: [],
            channels: {}
          }
        }
      });
    }
    return jsonResponse([]);
  });

  render(<App />);

  expect(screen.getByRole("banner")).toBeInTheDocument();
  expect(screen.getByRole("navigation", { name: "主导航" })).toBeInTheDocument();
  expect(screen.getByRole("heading", { name: "人才搜索与评估" })).toBeInTheDocument();
  expect(screen.getByRole("heading", { name: "岗位列表" })).toBeInTheDocument();
  expect(screen.getByRole("button", { name: "新建岗位" })).toBeInTheDocument();
  expect(screen.getByRole("button", { name: "岗位" })).toHaveAttribute("aria-pressed", "true");
  expect(screen.queryByText("Local sourcing workspace")).not.toBeInTheDocument();
});

it("keeps deployment status out of the HR workspace", async () => {
  vi.spyOn(globalThis, "fetch").mockImplementation(async (input) => {
    const url = String(input);
    if (url.endsWith("/api/system/status")) {
      return jsonResponse({
        environment: "vercel",
        deployment_ready: false,
        warnings: [],
        delivery_resources: {
          production_url: "https://talent-sourcing-tool-zeta.vercel.app",
          local_url: "http://127.0.0.1:5173",
          owner_checklist_path: "docs/production-owner-checklist.md",
          runbook_path: "docs/vercel-production-runbook-2026-07-29.md",
          verification_commands: [
            "python3 scripts/prepare_vercel_env.py --strict",
            "vercel --prod --yes",
            "./scripts/verify_production.sh"
          ],
          owner_prompts: [
            "TALENT_DATABASE_URL 由谁提供",
            "TALENT_OPENAI_API_KEY 由谁提供"
          ]
        },
        hard_blockers: [
          {
            code: "durable_storage_missing",
            message:
              "Production is using temporary SQLite storage on /tmp. Configure DATABASE_URL for durable state.",
            env_vars: ["DATABASE_URL", "TALENT_DATABASE_URL"]
          },
        {
          code: "review_provider_missing_key",
          message:
              "AI review is not configured for deployment. Set TALENT_OPENAI_API_KEY.",
          env_vars: ["TALENT_OPENAI_API_KEY"]
        }
        ],
        optional_degradations: [
          {
            code: "optional_channel_unavailable",
            message: "Optional production channel unavailable: Bright Data Discover.",
            env_vars: ["TALENT_BRIGHTDATA_API_KEY", "TALENT_BRIGHTDATA_ZONE"]
          }
        ],
        capabilities: {
          persistent_storage_configured: false,
          review_provider: "openai",
          review_configured: false,
          linkedin_configured: false,
          exa_configured: false,
          brightdata_configured: false,
          public_channels: ["github", "openreview", "arxiv"],
          required_channels: ["linkedin", "github", "openreview", "arxiv", "exa"],
          optional_channels: ["brightdata_discover"],
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
      });
    }
    if (url.endsWith("/api/system/provider-checks")) {
      return jsonResponse({
        providers: {
          exa: {
            status: "ok",
            detail: "Exa API key accepted a search request."
          },
          brightdata: {
            status: "expired_key",
            detail: "Bright Data API key exists but is expired."
          }
        }
      });
    }
    return jsonResponse([]);
  });

  render(<App />);

  expect(await screen.findByRole("heading", { name: "人才搜索与评估" })).toBeInTheDocument();
  expect(screen.queryByText("Operational status")).not.toBeInTheDocument();
  expect(screen.queryByRole("region", { name: "Deployment readiness" })).not.toBeInTheDocument();
  expect(screen.queryByRole("region", { name: "Delivery handoff" })).not.toBeInTheDocument();
  expect(screen.queryByRole("region", { name: "System warnings" })).not.toBeInTheDocument();
});

it("switches between shell tabs without routing dependencies", () => {
  vi.spyOn(globalThis, "fetch").mockImplementation(async () => jsonResponse([]));
  render(<App />);

  fireEvent.click(screen.getByRole("button", { name: "搜索" }));

  expect(screen.getByRole("heading", { name: "搜索任务" })).toBeInTheDocument();
  expect(screen.getByRole("button", { name: "搜索" })).toHaveAttribute("aria-pressed", "true");
});

it("opens refinements and ignores late job loads after unmount", async () => {
  let resolveJobs: (response: Response) => void = () => undefined;
  vi.spyOn(globalThis, "fetch").mockImplementation(async (input) => {
    const url = String(input);
    if (url.endsWith("/api/jobs")) {
      return new Promise<Response>((resolve) => {
        resolveJobs = resolve;
      });
    }
    if (url.endsWith("/api/system/status")) {
      return jsonResponse({
        environment: "local",
        deployment_ready: true,
        warnings: [],
        capabilities: {
          persistent_storage_configured: true,
          review_provider: "codex",
          review_configured: true,
          linkedin_configured: true,
          exa_configured: true,
          brightdata_configured: true,
          public_channels: ["github", "openreview", "arxiv"],
          required_channels: ["linkedin", "github", "openreview", "arxiv", "exa"],
          optional_channels: ["brightdata_discover"],
          channel_availability: {
            linkedin: true,
            github: true,
            openreview: true,
            arxiv: true,
            exa: true,
            brightdata_discover: true
          },
          missing_env_vars: {
            storage: [],
            review: [],
            channels: {}
          }
        }
      });
    }
    return jsonResponse([]);
  });

  const { unmount } = render(<App />);

  fireEvent.click(screen.getByRole("button", { name: "岗位优化" }));
  expect(screen.getByRole("heading", { name: "岗位优化建议" })).toBeInTheDocument();

  unmount();
  resolveJobs(await jsonResponse([jobWithRubric.job]));
});

it("creates a job, displays its rubric, and uses it for search and candidates", async () => {
  vi.spyOn(globalThis, "fetch").mockImplementation(async (input, init) => {
    const url = String(input);
    const method = init?.method ?? "GET";
    if (url.endsWith("/api/system/status")) {
      return jsonResponse({
        environment: "local",
        deployment_ready: true,
        warnings: [],
        capabilities: {
          persistent_storage_configured: true,
          review_provider: "codex",
          review_configured: true,
          linkedin_configured: true,
          exa_configured: true,
          brightdata_configured: true,
          public_channels: ["github", "openreview", "arxiv"],
          required_channels: ["linkedin", "github", "openreview", "arxiv", "exa"],
          optional_channels: ["brightdata_discover"],
          channel_availability: {
            linkedin: true,
            github: true,
            openreview: true,
            arxiv: true,
            exa: true,
            brightdata_discover: true
          },
          missing_env_vars: {
            storage: [],
            review: [],
            channels: {}
          }
        }
      });
    }
    if (url.endsWith("/api/jobs") && method === "GET") {
      return jsonResponse([]);
    }
    if (url.endsWith("/api/jobs") && method === "POST") {
      return jsonResponse(jobWithRubric);
    }
    if (url.endsWith("/api/jobs/job_1")) {
      return jsonResponse(jobWithRubric);
    }
    if (url.endsWith("/api/search?job_id=job_1")) {
      return jsonResponse([]);
    }
    if (url.endsWith("/api/search") && method === "POST") {
      return jsonResponse({
        id: "search_run_1",
        job_id: "job_1",
        query: "AI product marketer",
        provider: "bright_data",
        channels: ["linkedin"],
        status: "pending",
        params: { limit: 10, region: "San Francisco, CA" },
        progress: { worker: 1, stage: "queued", total_channels: 1, completed_channels: 0 },
        candidate_count: 0,
        created_at: "2026-07-31T00:00:00Z",
        completed_at: null
      });
    }
    if (url.endsWith("/api/search/search_run_1/run") && method === "POST") {
      return jsonResponse({
        id: "search_run_1",
        job_id: "job_1",
        query: "AI product marketer",
        provider: "bright_data",
        channels: ["linkedin"],
        status: "completed",
        params: { limit: 10, region: "San Francisco, CA" },
        progress: { worker: 1, stage: "completed", total_channels: 1, completed_channels: 1 },
        candidate_count: 1,
        created_at: "2026-07-31T00:00:00Z",
        completed_at: "2026-07-31T00:01:00Z",
        candidates: searchRunResult.candidates
      });
    }
    if (url.endsWith("/api/candidates?job_id=job_1")) {
      return jsonResponse(searchRunResult.candidates);
    }
    return jsonResponse(null);
  });

  render(<App />);

  fireEvent.click(screen.getByRole("button", { name: "新建岗位" }));
  fireEvent.change(await screen.findByLabelText("岗位名称"), {
    target: { value: "Founding PMM" }
  });
  fireEvent.change(screen.getByLabelText("职位描述"), {
    target: { value: "Own positioning for AI launch." }
  });
  fireEvent.click(screen.getByRole("button", { name: "保存岗位" }));

  expect(await screen.findByText("Founder-market judgment")).toBeInTheDocument();

  fireEvent.click(screen.getByRole("button", { name: "搜索" }));
  fireEvent.change(await screen.findByLabelText("搜索条件"), {
    target: { value: "AI product marketer" }
  });
  fireEvent.click(screen.getByRole("button", { name: "创建搜索任务" }));

  expect(await screen.findByText("Searched Candidate")).toBeInTheDocument();
});

it("starts review, drafts a pass reason, and submits pass feedback", async () => {
  vi.spyOn(globalThis, "fetch").mockImplementation(async (input, init) => {
    const url = String(input);
    const method = init?.method ?? "GET";
    if (url.endsWith("/api/system/status")) {
      return jsonResponse({
        environment: "vercel",
        deployment_ready: false,
        warnings: [
          "Production is using temporary SQLite storage on /tmp. Configure DATABASE_URL for durable state."
        ],
        capabilities: {
          persistent_storage_configured: false,
          review_provider: "openai",
          review_configured: false,
          linkedin_configured: false,
          exa_configured: false,
          brightdata_configured: false,
          public_channels: ["github", "openreview", "arxiv"],
          required_channels: ["linkedin", "github", "openreview", "arxiv", "exa"],
          optional_channels: ["brightdata_discover"],
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
      });
    }
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

  fireEvent.click(await screen.findByRole("button", { name: "候选人" }));
  fireEvent.click(await screen.findByRole("button", { name: "评审 Searched Candidate" }));
  expect(
    await screen.findByText(
      "当前部署尚未完成生产评审配置，暂时无法使用 AI 评审。"
    )
  ).toBeInTheDocument();
  expect(screen.getByRole("button", { name: "开始 AI 评审" })).toBeDisabled();

  fireEvent.click(screen.getByRole("button", { name: "返回候选人" }));
  expect(await screen.findByRole("heading", { name: "候选人" })).toBeInTheDocument();
});

const jobWithRubric = {
  job: {
    id: "job_1",
    title: "Founding PMM",
    description: "Own positioning for AI launch.",
    region: "San Francisco, CA",
    target_profile_text: "",
    red_flags_text: "",
    search_notes: "",
    search_channels: ["linkedin", "exa", "brightdata_discover"],
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
      profile_url: "https://www.linkedin.com/in/searched",
      profile_source: "linkedin",
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

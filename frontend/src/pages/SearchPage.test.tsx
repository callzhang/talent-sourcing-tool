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
          progress: {
            worker: 1,
            stage: "completed",
            total_channels: 4,
            completed_channels: 4,
            active_channel: null,
            channel_errors: { linkedin: "上游服务不可用" },
            error_message: "LinkedIn upstream unavailable"
          },
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
        progress: {
          worker: 1,
          stage: "completed",
          total_channels: 4,
            completed_channels: 4,
            active_channel: null,
            channel_errors: { linkedin: "上游服务不可用" },
            error_message: "LinkedIn upstream unavailable"
        },
        candidate_count: 1,
        created_at: "2026-04-28T12:00:00Z",
        completed_at: "2026-04-28T12:01:00Z",
        candidates: [persistedCandidate]
      });
    }
    if (url.endsWith("/api/search/search_run_new") && method === "GET") {
      return jsonResponse({
        id: "search_run_new",
        job_id: "job_1",
        query: "Search configured from the JD",
        provider: "bright_data",
        channels: ["linkedin", "github", "exa", "brightdata_discover"],
        status: "pending",
        params: { limit: 2, region: "San Francisco, CA" },
        progress: { worker: 1, stage: "searching", total_channels: 4, completed_channels: 1 },
        candidate_count: 0,
        created_at: "2026-07-31T00:00:00Z",
        completed_at: null,
        candidates: []
      });
    }
    if (url.endsWith("/api/search") && method === "POST") {
      return jsonResponse({
        id: "search_run_new",
        job_id: "job_1",
        query: "Search configured from the JD",
        provider: "bright_data",
        channels: ["linkedin", "github", "exa", "brightdata_discover"],
        status: "pending",
        params: { limit: 2, region: "San Francisco, CA" },
        progress: { worker: 1, stage: "queued", total_channels: 4, completed_channels: 0 },
        candidate_count: 0,
        created_at: "2026-07-31T00:00:00Z",
        completed_at: null
      });
    }
    if (url.endsWith("/api/search/search_run_new/run") && method === "POST") {
      return jsonResponse({
        id: "search_run_new",
        job_id: "job_1",
        query: "Search configured from the JD",
        provider: "bright_data",
        channels: ["linkedin", "github", "exa", "brightdata_discover"],
        status: "completed",
        params: { limit: 2, region: "San Francisco, CA" },
        progress: { worker: 1, stage: "completed", total_channels: 4, completed_channels: 4 },
        candidate_count: 1,
        created_at: "2026-07-31T00:00:00Z",
        completed_at: "2026-07-31T00:01:00Z",
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
  expect(screen.getAllByText("搜索渠道")).toHaveLength(2);
  expect(await screen.findByText("LinkedIn 失败：上游服务不可用")).toBeInTheDocument();
  expect(await screen.findByText("任务失败：LinkedIn upstream unavailable")).toBeInTheDocument();

  fireEvent.change(screen.getByLabelText("候选人数量"), {
    target: { value: "2" }
  });
  fireEvent.submit(screen.getByLabelText("搜索条件").closest("form") as HTMLFormElement);

  await waitFor(() => expect(onCandidatesFound).toHaveBeenCalledWith([candidate]));
  expect(await screen.findByText("搜索完成，找到 1 位候选人。")).toBeInTheDocument();
  expect(screen.getByText("New Candidate")).toBeInTheDocument();
  fireEvent.click(screen.getByRole("button", { name: "查看 Persisted Candidate" }));
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

  fireEvent.change(screen.getByLabelText("搜索条件"), {
    target: { value: "ai builders" }
  });
  fireEvent.submit(screen.getByLabelText("搜索条件").closest("form") as HTMLFormElement);

  expect(screen.getByText("请先创建或选择岗位。")).toBeInTheDocument();
});

it("persists a queued run immediately and reports its worker progress", async () => {
  let resolveRun: (value: Response) => void = () => undefined;
  const fetchMock = vi.spyOn(globalThis, "fetch").mockImplementation(async (input, init) => {
    const url = String(input);
    const method = init?.method ?? "GET";
    if (url.endsWith("/api/search?job_id=job_1") && method === "GET") {
      return jsonResponse([]);
    }
    if (url.endsWith("/api/search") && method === "POST") {
      return jsonResponse({
        id: "search_run_new",
        job_id: "job_1",
        query: "Search configured from the JD",
        provider: "bright_data",
        channels: ["linkedin", "github", "exa", "brightdata_discover"],
        status: "pending",
        params: { limit: 10, region: "San Francisco, CA" },
        progress: { worker: 1, stage: "queued", total_channels: 4, completed_channels: 0 },
        candidate_count: 0,
        created_at: "2026-07-31T00:00:00Z",
        completed_at: null
      });
    }
    if (url.endsWith("/api/search/search_run_new/run") && method === "POST") {
      return new Promise<Response>((resolve) => {
        resolveRun = resolve;
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

  fireEvent.click(screen.getByRole("button", { name: "创建搜索任务" }));
  expect(
    await screen.findByText(
      "正在通过 LinkedIn + GitHub + Exa + Bright Data Discover 搜索候选人..."
    )
  ).toBeInTheDocument();

  expect(await screen.findByText("1 条已保存记录")).toBeInTheDocument();
  expect(screen.getByText("等待执行 · 0 位候选人")).toBeInTheDocument();
  expect(screen.getByLabelText("执行器 1；已完成 0/4 个渠道")).toBeInTheDocument();
  await waitFor(() =>
    expect(fetchMock).toHaveBeenCalledWith(
      "/api/search/search_run_new/run",
      expect.objectContaining({ method: "POST" })
    )
  );

  resolveRun(
    await jsonResponse({
      id: "search_run_new",
      job_id: "job_1",
      query: "Search configured from the JD",
      provider: "bright_data",
      channels: ["linkedin", "github", "exa", "brightdata_discover"],
      status: "completed",
      params: { limit: 10, region: "San Francisco, CA" },
      progress: { worker: 1, stage: "completed", total_channels: 4, completed_channels: 4 },
      candidate_count: 1,
      created_at: "2026-07-31T00:00:00Z",
      completed_at: "2026-07-31T00:01:00Z",
      candidates: [candidate]
    })
  );
  expect(await screen.findByText("搜索完成，找到 1 位候选人。")).toBeInTheDocument();
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

  fireEvent.change(screen.getByLabelText("搜索条件"), {
    target: { value: "ai builders" }
  });
  fireEvent.click(screen.getByRole("button", { name: "创建搜索任务" }));

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

  fireEvent.change(screen.getByLabelText("岗位"), {
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
  expect(screen.getAllByText("暂不可用")).toHaveLength(3);
  expect(screen.getByRole("checkbox", { name: /Exa/ })).toBeDisabled();
  expect(screen.getByRole("checkbox", { name: /Bright Data Discover/ })).toBeDisabled();
  expect(screen.getByRole("checkbox", { name: /GitHub/ })).toBeChecked();
  expect(screen.getByRole("button", { name: "创建搜索任务" })).toBeDisabled();
  expect(
    screen.getByText("当前生产环境未配置持久化数据库，无法搜索。")
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

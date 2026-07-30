import "@testing-library/jest-dom/vitest";
import {
  act,
  cleanup,
  fireEvent,
  render,
  screen,
  waitFor,
  within
} from "@testing-library/react";
import { afterEach, expect, it, vi } from "vitest";

import { CandidateDetailPage } from "./CandidateDetailPage";
import type { Candidate } from "../types";

afterEach(() => {
  cleanup();
  vi.useRealTimers();
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
    if (url.endsWith("/api/reviews/latest-job?job_id=job_1&candidate_id=candidate_1")) {
      return jsonResponse(null);
    }
    if (url.endsWith("/api/candidates/candidate_2?job_id=job_1")) {
      return new Promise<Response>(() => undefined);
    }
    if (url.endsWith("/api/reviews/latest?job_id=job_1&candidate_id=candidate_2")) {
      return new Promise<Response>(() => undefined);
    }
    if (url.endsWith("/api/reviews/latest-job?job_id=job_1&candidate_id=candidate_2")) {
      return new Promise<Response>(() => undefined);
    }
    if (url.endsWith("/api/reviews/decision") && method === "POST") {
      return jsonResponse({ id: "decision_1" });
    }
    return jsonResponse(null);
  });

  const { rerender } = render(
    <CandidateDetailPage
      selectedJobId="job_1"
      candidate={candidateOne}
      systemStatus={null}
      onBack={() => undefined}
    />
  );

  expect(await screen.findByText("已加载最近一次评审。")).toBeInTheDocument();
  expect(screen.getByText("已完成")).toBeInTheDocument();
  expect(screen.getByRole("button", { name: "确认推进" })).toBeEnabled();

  rerender(
    <CandidateDetailPage selectedJobId="job_1" candidate={candidateTwo} onBack={() => undefined} />
  );

  expect(screen.getByText("正在加载候选人评审信息...")).toBeInTheDocument();
  expect(screen.queryByRole("button", { name: "确认推进" })).not.toBeInTheDocument();
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
    if (url.endsWith("/api/reviews/latest-job?job_id=job_1&candidate_id=candidate_1")) {
      return jsonResponse(null);
    }
    if (url.endsWith("/api/candidates/candidate_2?job_id=job_1")) {
      return jsonResponse(candidateTwo);
    }
    if (url.endsWith("/api/reviews/latest?job_id=job_1&candidate_id=candidate_2")) {
      return jsonResponse(null);
    }
    if (url.endsWith("/api/reviews/latest-job?job_id=job_1&candidate_id=candidate_2")) {
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
    <CandidateDetailPage
      selectedJobId="job_1"
      candidate={candidateOne}
      systemStatus={null}
      onBack={() => undefined}
    />
  );

  expect(await screen.findByText("已准备好进行 AI 评审。")).toBeInTheDocument();
  fireEvent.click(screen.getByRole("button", { name: "开始 AI 评审" }));
  expect(await screen.findByText("正在进行 AI 评审...")).toBeInTheDocument();
  expect(screen.getByText("进行中")).toBeInTheDocument();
  expect(screen.getByRole("button", { name: "确认推进" })).toBeDisabled();

  rerender(
    <CandidateDetailPage selectedJobId="job_1" candidate={candidateTwo} onBack={() => undefined} />
  );

  expect(await screen.findByRole("heading", { name: "Candidate Two" })).toBeInTheDocument();

  await act(async () => {
    resolveStaleReview(await jsonResponse(startReviewOne));
  });

  expect(screen.queryByText("Candidate one review summary.")).not.toBeInTheDocument();
  expect(screen.getByText("开始 AI 评审后，可查看评分、建议和证据。")).toBeInTheDocument();
  expect(screen.getByRole("button", { name: "生成淘汰原因草稿" })).toBeDisabled();
  expect(screen.getByRole("button", { name: "确认推进" })).toBeDisabled();
  expect(decisionPayloads).toHaveLength(0);
});

it("renders empty state and calls back when no candidate is selected", () => {
  const onBack = vi.fn();

  render(
    <CandidateDetailPage selectedJobId="job_1" candidate={null} systemStatus={null} onBack={onBack} />
  );

  expect(screen.getByText("请选择已搜索到的候选人进行评审。")).toBeInTheDocument();
  fireEvent.click(screen.getByRole("button", { name: "返回候选人" }));
  expect(onBack).toHaveBeenCalled();
});

it("surfaces review, draft, validation, and decision errors", async () => {
  vi.spyOn(globalThis, "fetch").mockImplementation(async (input, init) => {
    const url = String(input);
    const method = init?.method ?? "GET";
    if (url.endsWith("/api/candidates/candidate_1?job_id=job_1")) {
      return jsonResponse(candidateOne);
    }
    if (url.endsWith("/api/reviews/latest?job_id=job_1&candidate_id=candidate_1")) {
      return jsonResponse(reviewOne);
    }
    if (url.endsWith("/api/reviews/latest-job?job_id=job_1&candidate_id=candidate_1")) {
      return jsonResponse(null);
    }
    if (url.endsWith("/api/reviews/start") && method === "POST") {
      return errorResponse("Review worker failed");
    }
    if (url.endsWith("/api/reviews/review_1/draft-pass-reason")) {
      return errorResponse("Draft failed");
    }
    if (url.endsWith("/api/reviews/decision") && method === "POST") {
      return errorResponse("Decision failed");
    }
    return jsonResponse(null);
  });

  render(
    <CandidateDetailPage
      selectedJobId="job_1"
      candidate={candidateOne}
      systemStatus={null}
      onBack={() => undefined}
    />
  );

  expect(await screen.findByText("Candidate one summary.")).toBeInTheDocument();
  expect(screen.getByText("已完成")).toBeInTheDocument();
  fireEvent.click(screen.getByRole("button", { name: "开始 AI 评审" }));
  expect(await screen.findByText("POST /api/reviews/start failed with 500: Review worker failed")).toBeInTheDocument();
  expect(screen.getByText("已完成")).toBeInTheDocument();
  expect(screen.getByRole("button", { name: "生成淘汰原因草稿" })).toBeEnabled();

  fireEvent.click(screen.getByRole("button", { name: "生成淘汰原因草稿" }));
  expect(await screen.findByText("GET /api/reviews/review_1/draft-pass-reason failed with 500: Draft failed")).toBeInTheDocument();
  expect(screen.getByText("已完成")).toBeInTheDocument();
  expect(screen.getByRole("button", { name: "确认淘汰" })).toBeEnabled();

  fireEvent.click(screen.getByRole("button", { name: "确认淘汰" }));
  expect(screen.getByText("淘汰决定必须填写原因。")).toBeInTheDocument();

  fireEvent.change(screen.getByLabelText("淘汰原因"), {
    target: { value: "Not enough public evidence." }
  });
  fireEvent.click(screen.getByRole("button", { name: "确认淘汰" }));
  expect(await screen.findByText("POST /api/reviews/decision failed with 500: Decision failed")).toBeInTheDocument();
});

it("renders review fallback fields and draft evidence", async () => {
  vi.spyOn(globalThis, "fetch").mockImplementation(async (input) => {
    const url = String(input);
    if (url.endsWith("/api/candidates/candidate_1?job_id=job_1")) {
      return jsonResponse(candidateOne);
    }
    if (url.endsWith("/api/reviews/latest?job_id=job_1&candidate_id=candidate_1")) {
      return jsonResponse({
        ...reviewOne,
        review: {
          evidence: [{}, { label: "Portfolio", url: "https://example.com" }]
        }
      });
    }
    if (url.endsWith("/api/reviews/latest-job?job_id=job_1&candidate_id=candidate_1")) {
      return jsonResponse(null);
    }
    if (url.endsWith("/api/reviews/review_1/draft-pass-reason")) {
      return jsonResponse({
        reason_code: "weak_builder_evidence",
        reason_text: "Weak builder evidence.",
        evidence: ["No shipped prototypes"]
      });
    }
    return jsonResponse(null);
  });

  render(
    <CandidateDetailPage
      selectedJobId="job_1"
      candidate={candidateOne}
      systemStatus={null}
      onBack={() => undefined}
    />
  );

  expect(await screen.findByText("暂无评分")).toBeInTheDocument();
  expect(screen.getByText("暂无建议")).toBeInTheDocument();
  expect(screen.getByText("未返回评审摘要。")).toBeInTheDocument();
  expect(screen.getByText("证据 1")).toBeInTheDocument();
  expect(screen.getByText("无详情")).toBeInTheDocument();
  expect(screen.getByText("Portfolio")).toBeInTheDocument();
  expect(screen.getByText("https://example.com")).toBeInTheDocument();

  fireEvent.click(screen.getByRole("button", { name: "生成淘汰原因草稿" }));
  expect(await screen.findByText("No shipped prototypes")).toBeInTheDocument();
});

it("ignores a stale in-flight draft after the candidate changes", async () => {
  let resolveDraft: (response: Response) => void = () => undefined;
  vi.spyOn(globalThis, "fetch").mockImplementation(async (input) => {
    const url = String(input);
    if (url.endsWith("/api/candidates/candidate_1?job_id=job_1")) {
      return jsonResponse(candidateOne);
    }
    if (url.endsWith("/api/reviews/latest?job_id=job_1&candidate_id=candidate_1")) {
      return jsonResponse(reviewOne);
    }
    if (url.endsWith("/api/candidates/candidate_2?job_id=job_1")) {
      return jsonResponse(candidateTwo);
    }
    if (url.endsWith("/api/reviews/latest?job_id=job_1&candidate_id=candidate_2")) {
      return jsonResponse(null);
    }
    if (url.endsWith("/api/reviews/review_1/draft-pass-reason")) {
      return new Promise<Response>((resolve) => {
        resolveDraft = resolve;
      });
    }
    return jsonResponse(null);
  });

  const { rerender } = render(
    <CandidateDetailPage
      selectedJobId="job_1"
      candidate={candidateOne}
      systemStatus={null}
      onBack={() => undefined}
    />
  );

  expect(await screen.findByText("Candidate one summary.")).toBeInTheDocument();
  fireEvent.click(screen.getByRole("button", { name: "生成淘汰原因草稿" }));

  rerender(
    <CandidateDetailPage selectedJobId="job_1" candidate={candidateTwo} onBack={() => undefined} />
  );
  expect(await screen.findByRole("heading", { name: "Candidate Two" })).toBeInTheDocument();

  await act(async () => {
    resolveDraft(
      await jsonResponse({
        reason_code: "weak_builder_evidence",
        reason_text: "Stale draft",
        evidence: ["Stale evidence"]
      })
    );
  });

  expect(screen.queryByText("Stale evidence")).not.toBeInTheDocument();
});

it("disables AI review when deployment review config is incomplete", async () => {
  vi.spyOn(globalThis, "fetch").mockImplementation(async (input) => {
    const url = String(input);
    if (url.endsWith("/api/candidates/candidate_1?job_id=job_1")) {
      return jsonResponse(candidateOne);
    }
    if (url.endsWith("/api/reviews/latest?job_id=job_1&candidate_id=candidate_1")) {
      return jsonResponse(null);
    }
    return jsonResponse(null);
  });

  render(
    <CandidateDetailPage
      selectedJobId="job_1"
      candidate={candidateOne}
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
      onBack={() => undefined}
    />
  );

  expect(
    await screen.findByText(
      "当前部署尚未完成生产评审配置，暂时无法使用 AI 评审。"
    )
  ).toBeInTheDocument();
  expect(screen.getByRole("button", { name: "开始 AI 评审" })).toBeDisabled();
});

const candidateOne: Candidate = {
  id: "candidate_1",
  profile_url: "https://www.linkedin.com/in/one",
  profile_source: "linkedin",
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
  profile_url: "https://www.linkedin.com/in/two",
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
  status: "completed",
  review_id: "review_1",
  review: {
    candidate_id: "candidate_1",
    job_id: "job_1",
    decision_summary: "Candidate one review summary.",
    recommendation: "proceed",
    overall_score: 8
  }
};

it("polls review job status until the review is completed", async () => {
  let resolveReviewJob: (response: Response) => void = () => undefined;
  const fetchMock = vi.spyOn(globalThis, "fetch");
  fetchMock.mockImplementation(async (input, init) => {
    const url = String(input);
    const method = init?.method ?? "GET";
    if (url.endsWith("/api/candidates/candidate_1?job_id=job_1")) {
      return jsonResponse(candidateOne);
    }
    if (url.endsWith("/api/reviews/latest?job_id=job_1&candidate_id=candidate_1")) {
      return jsonResponse(null);
    }
    if (url.endsWith("/api/reviews/latest-job?job_id=job_1&candidate_id=candidate_1")) {
      return jsonResponse(null);
    }
    if (url.endsWith("/api/reviews/start") && method === "POST") {
      return jsonResponse({
        review_job_id: "review_job_queued",
        status: "running",
        review_id: null,
        review: null
      });
    }
    if (url.endsWith("/api/reviews/jobs/review_job_queued/run") && method === "POST") {
      return new Promise<Response>((resolve) => {
        resolveReviewJob = resolve;
      });
    }
    return jsonResponse(null);
  });

  render(
    <CandidateDetailPage
      selectedJobId="job_1"
      candidate={candidateOne}
      systemStatus={null}
      onBack={() => undefined}
    />
  );

  expect(await screen.findByText("已准备好进行 AI 评审。")).toBeInTheDocument();
  fireEvent.click(screen.getByRole("button", { name: "开始 AI 评审" }));
  expect(await screen.findByText("AI 评审进行中...")).toBeInTheDocument();
  expect(
    within(screen.getByLabelText("评审状态")).getByText("进行中", { exact: true })
  ).toBeInTheDocument();
  expect(screen.getByRole("button", { name: "确认推进" })).toBeDisabled();

  await act(async () => {
    resolveReviewJob(
      await jsonResponse({
        id: "review_job_queued",
        job_id: "job_1",
        candidate_id: "candidate_1",
        status: "completed",
        error_message: null,
        created_at: "2026-07-29T12:00:00Z",
        started_at: "2026-07-29T12:00:01Z",
        completed_at: "2026-07-29T12:00:05Z",
        review_id: "review_queued",
        review: {
          candidate_id: "candidate_1",
          job_id: "job_1",
          decision_summary: "Queued review summary.",
          recommendation: "proceed",
          overall_score: 7.4
        }
      })
    );
  });

  expect(await screen.findByText("Queued review summary.")).toBeInTheDocument();
  expect(screen.getByText("AI 评审已完成。")).toBeInTheDocument();
  expect(
    within(screen.getByLabelText("评审状态")).getByText("已完成", { exact: true })
  ).toBeInTheDocument();
  expect(screen.getByRole("button", { name: "确认推进" })).toBeEnabled();
});

it("restores a pending review job after the user leaves and reopens the candidate", async () => {
  const fetchMock = vi.spyOn(globalThis, "fetch");
  let latestJobCalls = 0;
  fetchMock.mockImplementation(async (input, init) => {
    const url = String(input);
    const method = init?.method ?? "GET";
    if (url.endsWith("/api/candidates/candidate_1?job_id=job_1")) {
      return jsonResponse(candidateOne);
    }
    if (url.endsWith("/api/reviews/latest?job_id=job_1&candidate_id=candidate_1")) {
      return jsonResponse(null);
    }
    if (url.endsWith("/api/reviews/latest-job?job_id=job_1&candidate_id=candidate_1")) {
      latestJobCalls += 1;
      if (latestJobCalls === 1) {
        return jsonResponse(null);
      }
      return jsonResponse({
        id: "review_job_queued",
        job_id: "job_1",
        candidate_id: "candidate_1",
        status: "pending",
        error_message: null,
        created_at: "2026-07-30T12:00:00Z",
        started_at: null,
        completed_at: null,
        review_id: null,
        review: null
      });
    }
    if (url.endsWith("/api/reviews/start") && method === "POST") {
      return jsonResponse({
        review_job_id: "review_job_queued",
        status: "pending",
        review_id: null,
        review: null
      });
    }
    if (url.endsWith("/api/reviews/jobs/review_job_queued/run") && method === "POST") {
      return jsonResponse({
        id: "review_job_queued",
        job_id: "job_1",
        candidate_id: "candidate_1",
        status: "completed",
        error_message: null,
        created_at: "2026-07-30T12:00:00Z",
        started_at: "2026-07-30T12:00:02Z",
        completed_at: "2026-07-30T12:00:10Z",
        review_id: "review_queued",
        review: {
          candidate_id: "candidate_1",
          job_id: "job_1",
          decision_summary: "Recovered queued review summary.",
          recommendation: "proceed",
          overall_score: 7.8
        }
      });
    }
    return jsonResponse(null);
  });

  const { rerender } = render(
    <CandidateDetailPage
      selectedJobId="job_1"
      candidate={candidateOne}
      systemStatus={null}
      onBack={() => undefined}
    />
  );

  expect(await screen.findByText("已准备好进行 AI 评审。")).toBeInTheDocument();
  fireEvent.click(screen.getByRole("button", { name: "开始 AI 评审" }));
  expect(await screen.findByText("AI 评审排队中...")).toBeInTheDocument();

  rerender(
    <CandidateDetailPage selectedJobId="job_1" candidate={null} onBack={() => undefined} />
  );
  rerender(
    <CandidateDetailPage
      selectedJobId="job_1"
      candidate={candidateOne}
      systemStatus={null}
      onBack={() => undefined}
    />
  );

  expect(await screen.findByText("Recovered queued review summary.")).toBeInTheDocument();
  expect(screen.getByText("AI 评审已完成。")).toBeInTheDocument();
  expect(screen.getByText("已完成")).toBeInTheDocument();
});

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

import type {
  Candidate,
  CandidateDecision,
  DraftPassReason,
  Job,
  JobWithRubric,
  RefinementSuggestion,
  ReviewRead,
  ReviewStartResult,
  SearchChannel,
  SearchRun,
  SearchRunDetail,
  SearchRunResult
} from "./types";

const DEFAULT_API_BASE_URL = "http://localhost:8000";

export const API_BASE_URL =
  import.meta.env.VITE_API_BASE_URL?.replace(/\/$/, "") ?? DEFAULT_API_BASE_URL;

type ApiErrorDetail = string | Record<string, unknown> | Array<Record<string, unknown>>;

export class ApiError extends Error {
  readonly status: number;
  readonly detail: ApiErrorDetail;

  constructor(method: string, path: string, status: number, detail: ApiErrorDetail) {
    const detailText = typeof detail === "string" ? detail : JSON.stringify(detail);
    super(`${method} ${path} failed with ${status}: ${detailText}`);
    this.name = "ApiError";
    this.status = status;
    this.detail = detail;
  }
}

type RequestOptions = Omit<RequestInit, "body"> & {
  body?: unknown;
};

async function responseBody(response: Response): Promise<unknown> {
  if (response.status === 204) {
    return undefined;
  }
  if (response.headers.get("Content-Type")?.includes("application/json")) {
    return response.json();
  }
  return response.text();
}

function errorDetail(body: unknown, fallback: string): ApiErrorDetail {
  if (typeof body === "object" && body !== null && "detail" in body) {
    const detail = (body as { detail: unknown }).detail;
    if (
      typeof detail === "string" ||
      (typeof detail === "object" && detail !== null)
    ) {
      return detail as ApiErrorDetail;
    }
  }
  if (typeof body === "string" && body.length > 0) {
    return body;
  }
  return fallback;
}

async function request<T>(path: string, options: RequestOptions = {}): Promise<T> {
  const method = options.method ?? "GET";
  const init: RequestInit = {
    ...options,
    headers: { "Content-Type": "application/json", ...options.headers },
    body: options.body === undefined ? undefined : JSON.stringify(options.body)
  };
  const response = await fetch(`${API_BASE_URL}${path}`, init);
  const body = await responseBody(response);

  if (!response.ok) {
    throw new ApiError(method, path, response.status, errorDetail(body, response.statusText));
  }

  return body as T;
}

export type CreateJobPayload = {
  title: string;
  description: string;
  target_profile_text?: string;
  red_flags_text?: string;
  search_notes?: string;
  search_channels?: SearchChannel[];
};

export type CreateSearchPayload = {
  job_id: string;
  query: string;
  provider?: string;
  channels?: SearchChannel[];
  params?: Record<string, unknown>;
};

export type StartReviewPayload = {
  job_id: string;
  candidate_id: string;
};

export type CreateDecisionPayload = {
  job_id: string;
  candidate_id: string;
  review_id?: string;
  decision: "pass" | "proceed";
  notes?: string;
  decided_by?: string;
  pass_reason_code?: string;
  pass_reason_text?: string;
};

export const api = {
  createJob(payload: CreateJobPayload) {
    return request<JobWithRubric>("/api/jobs", { method: "POST", body: payload });
  },
  listJobs() {
    return request<Job[]>("/api/jobs");
  },
  getJob(jobId: string) {
    return request<JobWithRubric>(`/api/jobs/${encodeURIComponent(jobId)}`);
  },
  createSearch(payload: CreateSearchPayload) {
    return request<SearchRunResult>("/api/search", { method: "POST", body: payload });
  },
  listSearchRuns(jobId?: string) {
    const query = jobId ? `?job_id=${encodeURIComponent(jobId)}` : "";
    return request<SearchRun[]>(`/api/search${query}`);
  },
  getSearchRun(searchRunId: string) {
    return request<SearchRunDetail>(`/api/search/${encodeURIComponent(searchRunId)}`);
  },
  listCandidates(jobId?: string) {
    const query = jobId ? `?job_id=${encodeURIComponent(jobId)}` : "";
    return request<Candidate[]>(`/api/candidates${query}`);
  },
  getCandidate(candidateId: string, jobId?: string) {
    const query = jobId ? `?job_id=${encodeURIComponent(jobId)}` : "";
    return request<Candidate>(`/api/candidates/${encodeURIComponent(candidateId)}${query}`);
  },
  startReview(payload: StartReviewPayload) {
    return request<ReviewStartResult>("/api/reviews/start", { method: "POST", body: payload });
  },
  getLatestReview(jobId: string, candidateId: string) {
    return request<ReviewRead | null>(
      `/api/reviews/latest?job_id=${encodeURIComponent(jobId)}&candidate_id=${encodeURIComponent(
        candidateId
      )}`
    );
  },
  getDraftPassReason(reviewId: string) {
    return request<DraftPassReason>(
      `/api/reviews/${encodeURIComponent(reviewId)}/draft-pass-reason`
    );
  },
  listRefinementSuggestions(jobId: string) {
    return request<RefinementSuggestion[]>(
      `/api/reviews/refinements?job_id=${encodeURIComponent(jobId)}`
    );
  },
  createDecision(payload: CreateDecisionPayload) {
    return request<CandidateDecision>("/api/reviews/decision", {
      method: "POST",
      body: payload
    });
  }
};

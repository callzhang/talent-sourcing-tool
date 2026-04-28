export type ISODateString = string;

export type Job = {
  id: string;
  title: string;
  description: string;
  region: string;
  target_profile_text: string;
  red_flags_text: string;
  search_notes: string;
  search_channels: SearchChannel[];
  created_at: ISODateString;
  updated_at: ISODateString;
};

export type SearchChannel =
  | "linkedin"
  | "github"
  | "openreview"
  | "arxiv"
  | "exa"
  | "brightdata_discover";

export type RubricDimension = {
  name: string;
  description?: string;
  signals?: string[];
  red_flags?: string[];
  weight?: number;
  scoring_guidance?: string;
  must_have_evidence?: string[];
};

export type Rubric = {
  id: string;
  job_id: string;
  version: number;
  source_hash: string;
  rubric: {
    dimensions: RubricDimension[];
    positive_signals?: string[];
    negative_signals?: string[];
    red_lines?: string[];
  };
  created_at: ISODateString;
  updated_at: ISODateString;
};

export type JobWithRubric = {
  job: Job;
  rubric: Rubric;
};

export type CandidateProfileData = Record<string, unknown> & {
  current_title?: string;
  raw?: unknown;
};

export type Candidate = {
  id: string;
  linkedin_url: string;
  name: string;
  headline: string | null;
  location: string | null;
  current_company: string | null;
  profile_data: CandidateProfileData;
  created_at: ISODateString;
  updated_at: ISODateString;
  last_search_run_id?: string | null;
  last_search_query?: string | null;
  last_search_rank?: number | null;
};

export type SearchRunResult = {
  id: string;
  status: "completed" | "failed" | "running" | string;
  candidates: Candidate[];
};

export type SearchRun = {
  id: string;
  job_id: string;
  query: string;
  provider: string;
  channels: SearchChannel[];
  status: string;
  params: Record<string, unknown>;
  candidate_count: number;
  created_at: ISODateString;
  completed_at: ISODateString | null;
};

export type SearchRunDetail = SearchRun & {
  candidates: Candidate[];
};

export type ReviewRecommendation = "pass" | "proceed" | string;

export type ReviewPayload = Record<string, unknown> & {
  candidate_id?: string;
  job_id?: string;
  overall_score?: number;
  recommendation?: ReviewRecommendation;
  decision_summary?: string;
  evidence?: Array<Record<string, unknown>>;
};

export type ReviewStartResult = {
  review_job_id: string;
  review_id: string;
  review: ReviewPayload;
};

export type ReviewRead = {
  id: string;
  review_job_id: string;
  job_id: string;
  candidate_id: string;
  summary: string;
  evidence: Array<Record<string, unknown>>;
  recommendation: ReviewRecommendation;
  score: number | null;
  review: ReviewPayload;
  created_at: ISODateString;
};

export type DraftPassReason = {
  reason_code: string;
  reason_text: string;
  evidence: string[];
};

export type CandidateDecision = {
  id: string;
  job_id: string;
  candidate_id: string;
  review_id: string | null;
  decision: "pass" | "proceed";
  notes: string | null;
  decided_by: string;
};

export type RefinementSuggestion = {
  id: string;
  job_id: string;
  pass_reason_id: string | null;
  suggestion_type: string;
  suggestion_text: string;
  status: string;
  suggestion_metadata: Record<string, unknown>;
  created_at: ISODateString;
  applied_at: ISODateString | null;
};

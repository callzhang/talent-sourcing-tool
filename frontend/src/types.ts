export type ISODateString = string;

export type SystemStatus = {
  environment: "local" | "vercel" | string;
  deployment_ready: boolean;
  warnings: string[];
  delivery_resources?: {
    production_url: string;
    local_url: string;
    owner_checklist_path: string;
    runbook_path: string;
    verification_commands: string[];
    owner_prompts: string[];
  };
  hard_blockers?: Array<{
    code: string;
    message: string;
    env_vars?: string[];
    channels?: string[];
  }>;
  optional_degradations?: Array<{
    code: string;
    message: string;
    env_vars?: string[];
    channels?: string[];
  }>;
  capabilities: {
    persistent_storage_configured: boolean;
    review_provider: string;
    review_configured: boolean;
    linkedin_configured?: boolean;
    exa_configured: boolean;
    brightdata_configured: boolean;
    public_channels: string[];
    required_channels?: SearchChannel[];
    optional_channels?: SearchChannel[];
    required_provider_checks?: string[];
    optional_provider_checks?: string[];
    channel_availability?: Partial<Record<SearchChannel, boolean>>;
    missing_env_vars?: {
      storage: string[];
      review: string[];
      channels: Partial<Record<SearchChannel, string[]>>;
    };
  };
};

export type ProviderChecks = {
  providers: {
    exa: {
      status: string;
      detail: string;
    };
    brightdata: {
      status: string;
      detail: string;
      active_zones?: string[];
    };
  };
};

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
  profile_url: string;
  profile_source: SearchChannel | string;
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
  status: string;
  review_id: string | null;
  review: ReviewPayload | null;
};

export type ReviewJob = {
  id: string;
  job_id: string;
  candidate_id: string;
  status: string;
  error_message: string | null;
  created_at: ISODateString;
  started_at: ISODateString | null;
  completed_at: ISODateString | null;
  review_id: string | null;
  review: ReviewPayload | null;
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

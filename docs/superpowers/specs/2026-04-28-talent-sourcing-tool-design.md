# Talent Sourcing Tool Design

Date: 2026-04-28

Status: Ready for user review

## 1. Purpose

Build a local-first internal talent sourcing tool for the US hiring effort.

The first version should support:

- JD management;
- AI-generated rubric creation from natural-language JD text;
- Bright Data-based LinkedIn talent search;
- candidate list management;
- deep AI review of each candidate;
- human feedback and `pass` / `proceed` decision;
- structured pass-reason capture;
- iterative improvement of JD, rubric, and search query based on pass/proceed outcomes.

The tool is not an ATS in v1. It does not manage contacted, interview, offer, or onboarding pipeline stages.

## 2. Scope

Implementation target after this design is approved:

- create a new repository under `/Users/derek/Documents/Projects/`;
- use a working name such as `talent-sourcing-tool` unless renamed before implementation;
- keep this memory repository as the design/reference workspace, not the application repo.

### In Scope

- Local web application.
- Single-user internal workflow.
- Python FastAPI backend.
- React/Vite frontend.
- Turso/libSQL database.
- Bright Data MCP / skill / API connector abstraction.
- LinkedIn candidate sourcing and LinkedIn profile URL deduplication.
- JD-to-rubric agent.
- Candidate AI review using local `codex exec`.
- Temporary review workspace and temporary `HOME` per review job.
- File-based Codex protocol: `input.json` in, `review.json` out.
- Codex review agent may use local browser-use/plugin capability to access the user's already logged-in LinkedIn session.
- Enrichment from public sources such as GitHub, X, blogs, news, personal websites, and project pages.
- Human feedback on AI review.
- Required pass reason when user decides `pass`.
- AI-assisted pass reason generation.
- Query/rubric/JD refinement recommendations from accumulated feedback.

### Out of Scope

- Vercel deployment in v1.
- Multi-user auth and role permissions.
- Full ATS pipeline.
- Automated outreach.
- Email/calendar integration.
- Candidate-facing flows.
- Background browser automation inside Vercel serverless.
- Guaranteed LinkedIn access reliability.
- Legal/compliance automation beyond audit fields and configurable data retention.

## 3. Key Decisions

| Topic | Decision |
| --- | --- |
| Deployment | Local-first for v1 |
| Backend | Python FastAPI |
| Frontend | React + Vite |
| Database | Turso/libSQL |
| Candidate identity | LinkedIn profile URL |
| JD rubric | Generated from natural language JD |
| Rubric customization | Natural-language first; future structured editor optional |
| Review output | Two-layer output: decision summary + evidence/source chain |
| Candidate decision | Only `pass` or `proceed` in v1 |
| Pass reason | Required for `pass`; AI may draft, user confirms |
| Review execution | Local `codex exec` with file protocol |
| Browser access | Codex may use local browser-use/plugin against existing logged-in LinkedIn profile |
| Database writes | Only backend writes to database; Codex writes files only |

## 4. User Workflow

1. User creates a JD.
2. User writes natural-language hiring criteria, target profile, positive signals, negative signals, and red lines.
3. Rubric agent converts JD text into structured dimensions, weights, scoring guidance, red flags, and evidence requirements.
4. User selects a JD and creates a search run.
5. User enters query and parameters.
6. Sourcing connector calls Bright Data MCP / skill / API and returns LinkedIn people results.
7. Backend normalizes results and upserts candidates by LinkedIn profile URL.
8. User reviews candidate list and starts deep AI review for selected candidates.
9. Backend creates a review job and temporary workspace.
10. Backend writes `input.json` containing JD, rubric, candidate source data, LinkedIn URL, allowed tasks, and output schema.
11. Backend invokes local `codex exec` with temporary `HOME`.
12. Codex accesses LinkedIn through local browser capability when needed, searches public web sources, and writes `review.json`.
13. Backend validates `review.json` against schema and stores the result.
14. User reads decision summary and evidence chain.
15. User adds feedback.
16. User chooses `proceed` or `pass`.
17. If user chooses `pass`, app requires pass reason. Agent can draft reason from review/rubric evidence; user edits and confirms.
18. Feedback loop agent uses pass/proceed outcomes to suggest JD, rubric, and query improvements.

Closed loop:

`JD/query -> candidates -> AI review -> human decision -> pass reason/proceed signal -> rubric/query refinement -> next search batch`

## 5. Architecture

### Components

#### Frontend

Pages:

- JD list and JD editor.
- Rubric preview page.
- Search run page.
- Candidate list.
- Candidate review detail.
- Feedback and pass reason capture.
- JD/query refinement suggestions.

Responsibilities:

- Provide user interface.
- Display review and source evidence.
- Require pass reason before finalizing `pass`.
- Allow user to accept/reject AI-generated recommendations.

#### FastAPI Backend

Responsibilities:

- Own REST API.
- Manage JD, rubric, search runs, candidates, reviews, decisions, and feedback.
- Wrap Bright Data connector.
- Create and monitor review jobs.
- Invoke `codex exec`.
- Validate all worker output.
- Write all persistent data to Turso.

Backend is the only database writer.

#### Sourcing Connector

Responsibilities:

- Abstract Bright Data MCP / skill / API behind one interface.
- Normalize search results.
- Preserve raw provider payload for audit.

Primary interface:

```python
search_people(jd_id: str, query: str, params: SearchParams) -> list[CandidateSourceResult]
```

The connector should support provider metadata so future sources can be added without changing candidate storage.

#### Rubric Agent

Responsibilities:

- Convert natural-language JD into structured rubric.
- Produce dimensions, weights, scoring guidance, red flags, positive signals, and evidence requirements.
- Later consume feedback loop recommendations and propose rubric changes.

Rubric generation should be reviewable by the user before sourcing.

#### Review Worker

Responsibilities:

- Build isolated temporary workspace.
- Build isolated temporary `HOME`.
- Write `input.json`.
- Run `codex exec`.
- Allow explicit browser/search capability for this review only.
- Require `review.json`.
- Return only file outputs to backend.

Review worker must not access the main repository, global memory, unrelated skills, or historical sessions unless explicitly configured.

#### Feedback Loop Agent

Responsibilities:

- Analyze decisions and pass reasons for a JD/search run.
- Suggest better JD language, rubric changes, query changes, and Bright Data parameter changes.
- Explain which feedback evidence motivated each suggestion.

This agent does not automatically mutate JD/query. User must approve changes.

## 6. Data Model

### Entity Overview

- `jobs`
- `rubrics`
- `search_runs`
- `search_results`
- `candidates`
- `candidate_sources`
- `review_jobs`
- `reviews`
- `review_sources`
- `candidate_decisions`
- `pass_reasons`
- `user_feedback`
- `refinement_suggestions`

### Tables

#### jobs

Stores JD and hiring context.

Fields:

- `id`
- `title`
- `description`
- `target_profile_text`
- `red_flags_text`
- `search_notes`
- `status`
- `created_at`
- `updated_at`

#### rubrics

Stores AI-generated rubric per JD.

Fields:

- `id`
- `job_id`
- `version`
- `rubric_json`
- `source_text_hash`
- `created_at`

`rubric_json` includes:

- dimensions;
- weights;
- scoring guidance;
- must-have evidence;
- positive signals;
- negative signals;
- red lines.

#### search_runs

Stores each sourcing attempt.

Fields:

- `id`
- `job_id`
- `query`
- `params_json`
- `provider`
- `status`
- `created_at`
- `completed_at`

#### search_results

Stores raw and normalized search output.

Fields:

- `id`
- `search_run_id`
- `candidate_id`
- `provider`
- `profile_url`
- `normalized_json`
- `raw_json`
- `created_at`

#### candidates

Stores canonical candidate record.

Fields:

- `id`
- `linkedin_url`
- `name`
- `headline`
- `location`
- `current_company`
- `current_title`
- `summary_json`
- `created_at`
- `updated_at`

Unique constraint:

- `linkedin_url`

#### candidate_sources

Stores enrichment identities and source links.

Fields:

- `id`
- `candidate_id`
- `source_type`
- `url`
- `title`
- `snippet`
- `confidence`
- `raw_json`
- `created_at`

Source types include:

- `linkedin`
- `github`
- `x`
- `blog`
- `news`
- `website`
- `other`

#### review_jobs

Tracks Codex review execution.

Fields:

- `id`
- `candidate_id`
- `job_id`
- `rubric_id`
- `status`
- `workspace_path`
- `input_json_path`
- `output_json_path`
- `error_message`
- `created_at`
- `started_at`
- `completed_at`

#### reviews

Stores structured review.

Fields:

- `id`
- `review_job_id`
- `candidate_id`
- `job_id`
- `overall_score`
- `recommendation`
- `summary`
- `strengths_json`
- `risks_json`
- `dimension_scores_json`
- `evidence_json`
- `suggested_interview_questions_json`
- `raw_review_json`
- `created_at`

Recommendation enum:

- `strong_proceed`
- `proceed`
- `borderline`
- `pass`

This is AI recommendation only. User decision is stored separately.

#### review_sources

Stores cited review sources.

Fields:

- `id`
- `review_id`
- `source_type`
- `url`
- `title`
- `claim_supported`
- `confidence`
- `retrieved_at`

#### candidate_decisions

Stores final human decision for a candidate against a job.

Fields:

- `id`
- `candidate_id`
- `job_id`
- `decision`
- `decision_note`
- `created_at`
- `updated_at`

Decision enum:

- `pass`
- `proceed`

#### pass_reasons

Stores structured reason for pass decisions.

Fields:

- `id`
- `candidate_decision_id`
- `reason_code`
- `reason_text`
- `agent_suggested`
- `user_edited`
- `evidence_json`
- `created_at`

Example reason codes:

- `insufficient_ai_native_signal`
- `weak_builder_evidence`
- `too_enterprise_sales_oriented`
- `not_enough_0_to_1_experience`
- `weak_product_judgment`
- `not_senior_enough`
- `poor_mission_fit`
- `insufficient_public_evidence`
- `compensation_or_location_mismatch`

#### user_feedback

Stores user comments on AI review.

Fields:

- `id`
- `candidate_id`
- `job_id`
- `review_id`
- `feedback_text`
- `feedback_type`
- `created_at`

Feedback types:

- `correction`
- `additional_context`
- `review_quality`
- `rubric_feedback`
- `query_feedback`

#### refinement_suggestions

Stores agent-generated recommendations.

Fields:

- `id`
- `job_id`
- `source_scope`
- `suggestion_type`
- `suggestion_text`
- `evidence_json`
- `status`
- `created_at`
- `resolved_at`

Suggestion types:

- `jd_rewrite`
- `rubric_adjustment`
- `query_rewrite`
- `search_param_change`
- `negative_signal`
- `positive_signal`

Status:

- `new`
- `accepted`
- `rejected`
- `applied`

## 7. Codex Review File Protocol

### input.json

Backend writes `input.json` into review workspace.

Required fields:

```json
{
  "review_job_id": "string",
  "candidate": {
    "id": "string",
    "linkedin_url": "string",
    "name": "string",
    "headline": "string",
    "known_profile": {}
  },
  "job": {
    "id": "string",
    "title": "string",
    "description": "string",
    "target_profile_text": "string",
    "red_flags_text": "string"
  },
  "rubric": {
    "version": 1,
    "dimensions": []
  },
  "allowed_tasks": [
    "visit_linkedin_profile",
    "search_public_web",
    "find_github",
    "find_x_or_blog",
    "score_against_rubric",
    "write_review_json"
  ],
  "output_schema_path": "review.schema.json"
}
```

### review.json

Codex must write `review.json`.

Required top-level fields:

```json
{
  "candidate_id": "string",
  "job_id": "string",
  "overall_score": 0,
  "recommendation": "proceed",
  "decision_summary": "string",
  "dimension_scores": [],
  "strengths": [],
  "risks": [],
  "evidence": [],
  "sources": [],
  "suggested_interview_questions": [],
  "uncertainties": [],
  "review_notes": "string"
}
```

Rules:

- All claims should cite a source when possible.
- If LinkedIn or external source cannot be accessed, review must state access limitation.
- Review must separate observed evidence from inference.
- Review must not fabricate missing credentials, employment dates, or projects.
- Review must include uncertainties when evidence is weak.

## 8. Pass Reason and Feedback Loop

When user selects `pass`, the app blocks finalization until pass reason exists.

Flow:

1. User clicks `pass`.
2. Backend asks pass-reason agent to draft likely reasons from review, rubric, and evidence.
3. UI shows reason code suggestions and plain-language explanation.
4. User confirms or edits.
5. Backend stores decision and pass reason.
6. Feedback loop agent aggregates pass reasons by JD/search run.
7. Agent proposes:
   - JD language changes;
   - rubric weighting changes;
   - new red flags;
   - search query exclusions;
   - positive signal boosts;
   - Bright Data parameter changes.
8. User chooses accept/reject/apply.

Proceed decisions should also store a short note, but note is optional in v1.

## 9. Error Handling

### Sourcing Errors

Cases:

- Bright Data unavailable.
- Query returns no results.
- Rate limit or provider error.
- Malformed provider payload.

Behavior:

- Store failed search run with error.
- Show retry option.
- Preserve query/params.
- Do not create candidates from invalid payloads.

### Review Errors

Cases:

- `codex exec` fails.
- `review.json` missing.
- `review.json` malformed.
- LinkedIn access blocked.
- Browser/plugin unavailable.
- Review times out.

Behavior:

- Mark review job `failed`.
- Store error message.
- Preserve workspace path until user clears it.
- Allow retry.
- If LinkedIn access fails but web evidence exists, review can be saved with access limitation.

### Data Validation Errors

Cases:

- Candidate URL invalid.
- Duplicate LinkedIn URL.
- Rubric JSON invalid.
- Pass decision without reason.

Behavior:

- Reject invalid writes.
- Return actionable UI error.
- Log validation failure.

## 10. Security and Privacy Boundaries

V1 is local-first and single-user, but still stores personal data.

Required boundaries:

- Store provider raw payloads only when necessary for audit.
- Store source URLs and snippets, not full scraped pages by default.
- Add future retention setting per JD/search run.
- Make export/delete candidate possible in a later version.
- Do not run high-frequency automated LinkedIn actions.
- Use human-triggered review jobs.
- Avoid automated outreach in v1.
- Keep Codex review workspace isolated from main repository and unrelated local files.

Known risk:

- Reusing an already logged-in LinkedIn browser profile is convenient but weaker isolation.
- If account risk becomes unacceptable, switch to dedicated sourcing browser profile.

## 11. Testing Strategy

### Unit Tests

- Rubric JSON validation.
- Candidate LinkedIn URL normalization.
- Candidate upsert deduplication.
- Search result normalization.
- Review JSON schema validation.
- Pass reason required for `pass`.
- Feedback loop input aggregation.

### Integration Tests

- Create JD -> generate rubric -> create search run -> import mock candidate -> run mock review -> decide pass/proceed.
- Failed Bright Data connector path.
- Failed Codex review path.
- Malformed `review.json` path.

### Manual Tests

- Bright Data search against a real query.
- Browser-use/plugin LinkedIn access from Codex review.
- GitHub/blog/news enrichment.
- User edits AI pass reason and saves.
- Refinement suggestions generated from multiple pass decisions.

### Golden Review Fixtures

Create fixed candidate fixtures:

- strong AI Product Engineer;
- weak traditional engineer;
- strong PMM;
- traditional enterprise sales false positive;
- insufficient public evidence candidate.

Use these to regression-test scoring and pass reasons.

## 12. Future Extensions

Possible v2 features:

- Vercel deployment with Turso.
- Multi-user auth.
- Role-based permissions.
- Dedicated browser worker.
- Dedicated LinkedIn sourcing profile.
- Full ATS pipeline.
- Automated outreach draft generation.
- Email/calendar integration.
- Export to external ATS.
- Structured rubric editor.
- Multi-provider sourcing: GitHub, Google, Exa, X, event attendee lists.
- Candidate comparison view.
- Team calibration metrics.

## 13. Open Risks

- LinkedIn logged-in automation may be brittle and may trigger account friction.
- Bright Data/MCP/API shape may require adapter changes after implementation starts.
- `codex exec` output can be verbose or malformed unless schema and prompts are strict.
- Natural-language rubric generation can encode vague criteria if JD input is vague.
- Candidate public evidence may be sparse; review must represent uncertainty honestly.
- Turso works for local-first and future hosted usage, but local dev setup needs clear env configuration.

## 14. Acceptance Criteria

MVP is acceptable when:

- User can create a JD.
- System can generate a structured rubric from natural-language JD.
- User can run a Bright Data LinkedIn search.
- Search results are normalized and deduplicated by LinkedIn URL.
- User can start candidate review.
- Review worker runs `codex exec` with temp workspace and writes `review.json`.
- Backend validates and stores review.
- UI shows decision summary and evidence chain.
- User can add feedback.
- User can choose `proceed`.
- User can choose `pass` only after confirming a pass reason.
- System can generate at least one JD/rubric/query refinement suggestion from pass reasons.

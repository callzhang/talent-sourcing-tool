# AI Product Engineer Flow Run - 2026-04-28

## Scope

This run exercised the first agreed talent profile: `AI Product Engineer - P1`.

The role contract used for the run:

- Build Friday-based AI product prototypes for US PMF discovery.
- Turn ambiguous customer problems into working demos and product hypotheses.
- Prioritize AI-native full-stack builders with strong vibe-coding velocity.
- Treat GTM-only, platform-only, solutions-only, and consulting-heavy profiles as red flags unless there is direct product-building evidence.

## Flow Result

The corrected end-to-end run completed successfully.

- Job ID: `job_6aa61698369e489fbaddb55e4ec39fbb`
- Search run ID: `search_run_632f2a92da5f47aba2d034f15567894e`
- Candidates retrieved: 10
- Candidates reviewed by local `codex exec` worker: 10
- Proceed decisions written: 6
- Pass or borderline decisions written: 4
- Refinement suggestions generated: 2

## Priority Candidates

Top 3 candidates to prioritize:

- Emily Zhang: score 91, `strong_proceed`. Strong AI-native full-stack prototype velocity, customer-facing prototype delivery, and product judgment.
- Nora Kim: score 89, `strong_proceed`. Strong forward-deployed AI builder profile with customer requirement synthesis, LangGraph/Next.js/Python, and eval loops.
- Alex Rivera: score 88, `strong_proceed`. Strong LLM workflow prototyping with design partners, customer-facing demos, and Python/TypeScript execution.

Proceed pool:

- Victoria Nguyen: score 86, `strong_proceed`. Strong agentic product engineer profile; validate artifact quality and current hands-on coding depth.
- Rachel Singh: score 80, `proceed`. Good demo-driven AI product engineering signal; validate shipped artifacts.
- Samir Patel: score 77, `proceed`. Good product-minded agentic prototype signal; validate public artifacts and depth.

Pass or hold:

- Lina Morales: score 68, `borderline`. Founder/product builder signal is useful, but evidence is not strong enough on hands-on AI/full-stack implementation.
- Jason Lee: score 52, `pass`. More solutions architecture than AI product engineering.
- Ben Owens: score 49, `pass`. More ML platform/infrastructure than customer-driven AI product prototyping.
- Owen Brooks: score 47, `pass`. GTM/consulting-heavy profile with unclear hands-on engineering depth.

## Process Findings

- The first real run exposed stale local SQLite schemas. Startup now applies lightweight SQLite migrations for current local schema fields.
- `codex exec` failed under a fully temporary `CODEX_HOME` because it lacked authentication. The worker now copies only `auth.json` into the temporary Codex home and still ignores user config/rules.
- `codex exec` also needed `--sandbox workspace-write` so it can write `review.json` in the generated review workspace.
- Passing all non-top-3 candidates was a bad recruiting decision policy. The corrected policy is: mark all `strong_proceed` and `proceed` candidates as proceed, mark top 3 in notes as priority, and reserve pass for actual mismatch or borderline cases.
- The review prompt now requires low-scoring dimensions to include structured `reason_code` values so pass reasons can feed query and rubric refinement.

## Generated Refinements

- Query rewrite: separate solutions architect searches from AI Product Engineer searches unless the candidate shows direct product-building ownership.
- Rubric adjustment: clarify builder-evidence criteria so reviewers distinguish hands-on shipping from advisory, leadership-only, or demo-light experience.

## Product Implications

- The current synchronous review path works but is slow for 10 candidates. A queue or background worker should be added before larger batches.
- The data model needs a first-class `shortlist` or `priority` state. Using only `pass/proceed` forces priority ranking into notes.
- Real Bright Data integration should preserve raw evidence links so the worker can move from profile-signal scoring to artifact-level scoring.

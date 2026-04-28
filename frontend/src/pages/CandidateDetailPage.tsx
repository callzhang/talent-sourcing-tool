import { FormEvent, useEffect, useRef, useState } from "react";

import { api } from "../api";
import type { Candidate, DraftPassReason, ReviewPayload, ReviewRead } from "../types";

type CandidateDetailPageProps = {
  selectedJobId: string | null;
  candidate: Candidate | null;
  onBack: () => void;
};

type ReviewContext = {
  reviewId: string;
  jobId: string;
  candidateId: string;
};

export function CandidateDetailPage({
  selectedJobId,
  candidate,
  onBack
}: CandidateDetailPageProps) {
  const [loadedCandidate, setLoadedCandidate] = useState<Candidate | null>(candidate);
  const [reviewContext, setReviewContext] = useState<ReviewContext | null>(null);
  const [review, setReview] = useState<ReviewPayload | null>(null);
  const [draft, setDraft] = useState<DraftPassReason | null>(null);
  const [notes, setNotes] = useState("");
  const [passReason, setPassReason] = useState("");
  const [status, setStatus] = useState("Ready for AI review.");
  const [isWorking, setIsWorking] = useState(false);
  const currentContextRef = useRef({
    selectedJobId,
    candidateId: candidate?.id ?? null,
    loadedCandidateId: loadedCandidate?.id ?? null,
    reviewContext
  });
  currentContextRef.current = {
    selectedJobId,
    candidateId: candidate?.id ?? null,
    loadedCandidateId: loadedCandidate?.id ?? null,
    reviewContext
  };
  const reviewId = reviewContext?.reviewId ?? null;

  useEffect(() => {
    setLoadedCandidate(null);
    setReviewContext(null);
    setReview(null);
    setDraft(null);
    setNotes("");
    setPassReason("");
    setIsWorking(false);

    if (!candidate || !selectedJobId) {
      setStatus("Ready for AI review.");
      return;
    }

    let ignore = false;
    setStatus("Loading candidate review context...");
    api
      .getCandidate(candidate.id, selectedJobId)
      .then((freshCandidate) => {
        if (!ignore) {
          setLoadedCandidate(freshCandidate);
        }
      })
      .catch(() => undefined);
    api
      .getLatestReview(selectedJobId, candidate.id)
      .then((latestReview: ReviewRead | null) => {
        if (!ignore && latestReview) {
          setReviewContext({
            reviewId: latestReview.id,
            jobId: latestReview.job_id,
            candidateId: latestReview.candidate_id
          });
          setReview(latestReview.review);
          setStatus("Loaded latest review.");
        } else if (!ignore) {
          setStatus("Ready for AI review.");
        }
      })
      .catch(() => undefined);
    return () => {
      ignore = true;
    };
  }, [candidate, selectedJobId]);

  const isCandidateContextReady =
    selectedJobId !== null &&
    candidate !== null &&
    loadedCandidate !== null &&
    loadedCandidate.id === candidate.id;

  function isCurrentCandidateContext(jobId: string, candidateId: string) {
    const currentContext = currentContextRef.current;
    return (
      currentContext.selectedJobId === jobId &&
      currentContext.candidateId === candidateId &&
      currentContext.loadedCandidateId === candidateId
    );
  }

  function isCurrentReviewContext(jobId: string, candidateId: string, activeReviewId: string) {
    const currentReviewContext = currentContextRef.current.reviewContext;
    return (
      isCurrentCandidateContext(jobId, candidateId) &&
      currentReviewContext?.jobId === jobId &&
      currentReviewContext.candidateId === candidateId &&
      currentReviewContext.reviewId === activeReviewId
    );
  }

  if (!selectedJobId || !candidate) {
    return (
      <section className="card">
        <button type="button" className="text-action" onClick={onBack}>
          Back to candidates
        </button>
        <h2>Candidate Review</h2>
        <p className="empty-state">Select a searched candidate to review.</p>
      </section>
    );
  }

  if (!isCandidateContextReady) {
    return (
      <section className="card">
        <button type="button" className="text-action" onClick={onBack}>
          Back to candidates
        </button>
        <h2>Candidate Review</h2>
        <p className="empty-state">Loading candidate review context...</p>
      </section>
    );
  }

  async function startReview() {
    /* c8 ignore next 3 -- UI renders the action only after selected job and candidate are loaded. */
    if (!selectedJobId || !loadedCandidate) {
      return;
    }
    const requestedJobId = selectedJobId;
    const requestedCandidateId = loadedCandidate.id;
    setIsWorking(true);
    setStatus("Running AI review...");
    try {
      const result = await api.startReview({
        job_id: requestedJobId,
        candidate_id: requestedCandidateId
      });
      if (!isCurrentCandidateContext(requestedJobId, requestedCandidateId)) {
        return;
      }
      setReviewContext({
        reviewId: result.review_id,
        jobId: requestedJobId,
        candidateId: requestedCandidateId
      });
      setReview(result.review);
      setDraft(null);
      setStatus("AI review completed.");
    } catch (error) {
      if (isCurrentCandidateContext(requestedJobId, requestedCandidateId)) {
        setStatus(error instanceof Error ? error.message : "Unable to start review.");
      }
    } finally {
      if (isCurrentCandidateContext(requestedJobId, requestedCandidateId)) {
        setIsWorking(false);
      }
    }
  }

  async function draftPassReason() {
    /* c8 ignore next 4 -- The draft button is disabled until a review context exists. */
    if (!reviewContext) {
      setStatus("Run a review before drafting a pass reason.");
      return;
    }
    const requestedReviewContext = reviewContext;
    setIsWorking(true);
    setStatus("Drafting pass reason...");
    try {
      const generatedDraft = await api.getDraftPassReason(requestedReviewContext.reviewId);
      if (
        !isCurrentReviewContext(
          requestedReviewContext.jobId,
          requestedReviewContext.candidateId,
          requestedReviewContext.reviewId
        )
      ) {
        return;
      }
      setDraft(generatedDraft);
      setPassReason(generatedDraft.reason_text);
      setStatus("Draft pass reason ready.");
    } catch (error) {
      if (
        isCurrentReviewContext(
          requestedReviewContext.jobId,
          requestedReviewContext.candidateId,
          requestedReviewContext.reviewId
        )
      ) {
        setStatus(error instanceof Error ? error.message : "Unable to draft pass reason.");
      }
    } finally {
      if (
        isCurrentReviewContext(
          requestedReviewContext.jobId,
          requestedReviewContext.candidateId,
          requestedReviewContext.reviewId
        )
      ) {
        setIsWorking(false);
      }
    }
  }

  async function submitDecision(decision: "pass" | "proceed") {
    /* c8 ignore next 3 -- Decision controls render only after candidate context is loaded. */
    if (!selectedJobId || !loadedCandidate) {
      return;
    }
    const requestedJobId = selectedJobId;
    const requestedCandidateId = loadedCandidate.id;
    const requestedReviewContext = reviewContext;
    const requestedDraft = draft;
    if (decision === "pass" && passReason.trim().length === 0) {
      setStatus("Pass decisions require a reason.");
      return;
    }
    if (
      !isCurrentCandidateContext(requestedJobId, requestedCandidateId) ||
      (requestedReviewContext !== null &&
        !isCurrentReviewContext(
          requestedReviewContext.jobId,
          requestedReviewContext.candidateId,
          requestedReviewContext.reviewId
        ))
    ) {
      /* c8 ignore next 2 -- This protects against stale event closures that are not user-reachable. */
      return;
    }
    setIsWorking(true);
    setStatus(`Saving ${decision} decision...`);
    try {
      await api.createDecision({
        job_id: requestedJobId,
        candidate_id: requestedCandidateId,
        review_id: requestedReviewContext?.reviewId,
        decision,
        notes,
        pass_reason_code: requestedDraft?.reason_code ?? "manual_pass",
        pass_reason_text: decision === "pass" ? passReason : undefined
      });
      if (isCurrentCandidateContext(requestedJobId, requestedCandidateId)) {
        setStatus(`Saved ${decision} decision.`);
      }
    } catch (error) {
      if (isCurrentCandidateContext(requestedJobId, requestedCandidateId)) {
        setStatus(error instanceof Error ? error.message : "Unable to save decision.");
      }
    } finally {
      if (isCurrentCandidateContext(requestedJobId, requestedCandidateId)) {
        setIsWorking(false);
      }
    }
  }

  function handleProceed(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    void submitDecision("proceed");
  }

  return (
    <section className="workspace-grid detail-grid" aria-labelledby="candidate-detail-heading">
      <div className="card">
        <button type="button" className="text-action" onClick={onBack}>
          Back to candidates
        </button>
        <p className="section-kicker">Candidate detail</p>
        <h2 id="candidate-detail-heading">{loadedCandidate.name}</h2>
        <p>{loadedCandidate.headline ?? "No headline captured"}</p>
        <p className="muted">
          {[loadedCandidate.current_company, loadedCandidate.location].filter(Boolean).join(" · ")}
        </p>
        <a href={loadedCandidate.linkedin_url} target="_blank" rel="noreferrer">
          Open LinkedIn profile
        </a>
        <button
          type="button"
          className="primary-action"
          onClick={startReview}
          disabled={isWorking}
        >
          Start AI review
        </button>
        <p className="muted">{status}</p>
      </div>

      <div className="card">
        <p className="section-kicker">AI review</p>
        <ReviewBlock review={review} />
        <button
          type="button"
          className="secondary-action"
          onClick={draftPassReason}
          disabled={isWorking || reviewId === null}
        >
          Draft pass reason
        </button>
        {draft ? <EvidenceList evidence={draft.evidence} /> : null}
      </div>

      <form className="card stack" onSubmit={handleProceed}>
        <p className="section-kicker">Human decision</p>
        <label>
          Decision notes and feedback
          <textarea value={notes} onChange={(event) => setNotes(event.target.value)} rows={4} />
        </label>
        <label>
          Pass reason
          <textarea
            value={passReason}
            onChange={(event) => setPassReason(event.target.value)}
            rows={4}
          />
        </label>
        <div className="action-row">
          <button type="button" className="danger-action" onClick={() => void submitDecision("pass")}>
            Submit pass
          </button>
          <button type="submit" className="primary-action">
            Submit proceed
          </button>
        </div>
      </form>
    </section>
  );
}

function ReviewBlock({ review }: { review: ReviewPayload | null }) {
  if (!review) {
    return <p className="empty-state">Start an AI review to see score, recommendation, and evidence.</p>;
  }
  return (
    <div className="review-block">
      <div className="score-badge">{review.overall_score ?? "No score"}</div>
      <h3>{review.recommendation ?? "No recommendation"}</h3>
      <p>{review.decision_summary ?? "No summary returned."}</p>
      <div className="evidence-grid">
        {(review.evidence ?? []).map((item, index) => (
          <article key={`${String(item.label ?? "evidence")}-${index}`} className="evidence-card">
            <strong>{String(item.label ?? `Evidence ${index + 1}`)}</strong>
            <span>{String(item.detail ?? item.url ?? "No detail")}</span>
          </article>
        ))}
      </div>
    </div>
  );
}

function EvidenceList({ evidence }: { evidence: string[] }) {
  return (
    <ul className="compact-list">
      {evidence.map((item) => (
        <li key={item}>{item}</li>
      ))}
    </ul>
  );
}

import { FormEvent, useEffect, useState } from "react";

import { api } from "../api";
import type { Candidate, DraftPassReason, ReviewPayload, ReviewRead } from "../types";

type CandidateDetailPageProps = {
  selectedJobId: string | null;
  candidate: Candidate | null;
  onBack: () => void;
};

export function CandidateDetailPage({
  selectedJobId,
  candidate,
  onBack
}: CandidateDetailPageProps) {
  const [loadedCandidate, setLoadedCandidate] = useState<Candidate | null>(candidate);
  const [reviewId, setReviewId] = useState<string | null>(null);
  const [review, setReview] = useState<ReviewPayload | null>(null);
  const [draft, setDraft] = useState<DraftPassReason | null>(null);
  const [notes, setNotes] = useState("");
  const [passReason, setPassReason] = useState("");
  const [status, setStatus] = useState("Ready for AI review.");
  const [isWorking, setIsWorking] = useState(false);

  useEffect(() => {
    if (!candidate || !selectedJobId) {
      return;
    }
    let ignore = false;
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
          setReviewId(latestReview.id);
          setReview(latestReview.review);
          setStatus("Loaded latest review.");
        }
      })
      .catch(() => undefined);
    return () => {
      ignore = true;
    };
  }, [candidate, selectedJobId]);

  if (!selectedJobId || !loadedCandidate) {
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

  async function startReview() {
    if (!selectedJobId || !loadedCandidate) {
      return;
    }
    setIsWorking(true);
    setStatus("Running AI review...");
    try {
      const result = await api.startReview({
        job_id: selectedJobId,
        candidate_id: loadedCandidate.id
      });
      setReviewId(result.review_id);
      setReview(result.review);
      setDraft(null);
      setStatus("AI review completed.");
    } catch (error) {
      setStatus(error instanceof Error ? error.message : "Unable to start review.");
    } finally {
      setIsWorking(false);
    }
  }

  async function draftPassReason() {
    if (!reviewId) {
      setStatus("Run a review before drafting a pass reason.");
      return;
    }
    setIsWorking(true);
    setStatus("Drafting pass reason...");
    try {
      const generatedDraft = await api.getDraftPassReason(reviewId);
      setDraft(generatedDraft);
      setPassReason(generatedDraft.reason_text);
      setStatus("Draft pass reason ready.");
    } catch (error) {
      setStatus(error instanceof Error ? error.message : "Unable to draft pass reason.");
    } finally {
      setIsWorking(false);
    }
  }

  async function submitDecision(decision: "pass" | "proceed") {
    if (!selectedJobId || !loadedCandidate) {
      return;
    }
    if (decision === "pass" && passReason.trim().length === 0) {
      setStatus("Pass decisions require a reason.");
      return;
    }
    setIsWorking(true);
    setStatus(`Saving ${decision} decision...`);
    try {
      await api.createDecision({
        job_id: selectedJobId,
        candidate_id: loadedCandidate.id,
        review_id: reviewId ?? undefined,
        decision,
        notes,
        pass_reason_code: draft?.reason_code ?? "manual_pass",
        pass_reason_text: decision === "pass" ? passReason : undefined
      });
      setStatus(`Saved ${decision} decision.`);
    } catch (error) {
      setStatus(error instanceof Error ? error.message : "Unable to save decision.");
    } finally {
      setIsWorking(false);
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

import { useEffect, useState } from "react";

import { api } from "../api";
import type { Candidate } from "../types";

type CandidatesPageProps = {
  selectedJobId: string | null;
  candidates: Candidate[];
  onLoadedCandidates: (candidates: Candidate[]) => void;
  onReviewCandidate: (candidate: Candidate) => void;
};

export function CandidatesPage({
  selectedJobId,
  candidates,
  onLoadedCandidates,
  onReviewCandidate
}: CandidatesPageProps) {
  const [status, setStatus] = useState("Loading searched candidates...");

  useEffect(() => {
    if (!selectedJobId) {
      setStatus("Select a JD before reviewing candidates.");
      return;
    }
    let ignore = false;
    api
      .listCandidates(selectedJobId)
      .then((loadedCandidates) => {
        if (ignore) {
          return;
        }
        onLoadedCandidates(loadedCandidates);
        setStatus(
          loadedCandidates.length > 0
            ? "Review candidates from completed search runs."
            : "No searched candidates for this JD yet."
        );
      })
      .catch((error: unknown) => {
        if (!ignore) {
          setStatus(error instanceof Error ? error.message : "Unable to load candidates.");
        }
      });
    return () => {
      ignore = true;
    };
  }, [onLoadedCandidates, selectedJobId]);

  return (
    <section className="card" aria-labelledby="candidates-heading">
      <p className="section-kicker">Candidate review queue</p>
      <h2 id="candidates-heading">Candidates</h2>
      <p className="muted">{status}</p>
      <div className="candidate-grid">
        {candidates.map((candidate) => (
          <article key={candidate.id} className="candidate-card">
            <div>
              <p className="rank-pill">
                {candidate.last_search_rank ? `Rank ${candidate.last_search_rank}` : "Sourced"}
              </p>
              <h3>{candidate.name}</h3>
              <p>{candidate.headline ?? "No headline captured"}</p>
              <p className="muted">
                {[candidate.current_company, candidate.location].filter(Boolean).join(" · ")}
              </p>
            </div>
            <a href={candidate.linkedin_url} target="_blank" rel="noreferrer">
              LinkedIn profile
            </a>
            <button
              type="button"
              className="secondary-action"
              onClick={() => onReviewCandidate(candidate)}
            >
              Review {candidate.name}
            </button>
          </article>
        ))}
      </div>
    </section>
  );
}

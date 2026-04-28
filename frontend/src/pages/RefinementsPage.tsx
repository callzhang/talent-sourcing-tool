import { useEffect, useState } from "react";

import { api } from "../api";
import type { Job, RefinementSuggestion } from "../types";

type RefinementsPageProps = {
  jobs: Job[];
  selectedJobId: string | null;
  onSelectJob: (jobId: string) => void;
};

export function RefinementsPage({ jobs, selectedJobId, onSelectJob }: RefinementsPageProps) {
  const [suggestions, setSuggestions] = useState<RefinementSuggestion[]>([]);
  const [status, setStatus] = useState("Select a JD to inspect persisted refinements.");

  useEffect(() => {
    if (!selectedJobId) {
      setSuggestions([]);
      return;
    }
    let ignore = false;
    api
      .listRefinementSuggestions(selectedJobId)
      .then((loadedSuggestions) => {
        if (!ignore) {
          setSuggestions(loadedSuggestions);
          setStatus(
            loadedSuggestions.length > 0
              ? "Persisted suggestions from pass reasons."
              : "No refinement suggestions yet."
          );
        }
      })
      .catch((error: unknown) => {
        if (!ignore) {
          setStatus(error instanceof Error ? error.message : "Unable to load refinements.");
        }
      });
    return () => {
      ignore = true;
    };
  }, [selectedJobId]);

  return (
    <section className="workspace-grid" aria-labelledby="refinements-heading">
      <div className="card">
        <p className="section-kicker">Feedback loop</p>
        <h2 id="refinements-heading">Refinement Suggestions</h2>
        <label>
          JD
          <select
            value={selectedJobId ?? ""}
            onChange={(event) => onSelectJob(event.target.value)}
          >
            <option value="" disabled>
              Select a JD
            </option>
            {jobs.map((job) => (
              <option key={job.id} value={job.id}>
                {job.title}
              </option>
            ))}
          </select>
        </label>
        <p className="muted">{status}</p>
      </div>

      <div className="card">
        <div className="refinement-grid">
          {suggestions.map((suggestion) => (
            <article key={suggestion.id} className="refinement-card">
              <p className="rank-pill">{suggestion.suggestion_type}</p>
              <h3>{suggestion.status}</h3>
              <p>{suggestion.suggestion_text}</p>
              <span>{reasonCodes(suggestion)}</span>
            </article>
          ))}
        </div>
      </div>
    </section>
  );
}

function reasonCodes(suggestion: RefinementSuggestion) {
  const reasonCodesValue = suggestion.suggestion_metadata.reason_codes;
  if (!Array.isArray(reasonCodesValue) || reasonCodesValue.length === 0) {
    return "No reason code metadata";
  }
  return reasonCodesValue.map(String).join(", ");
}

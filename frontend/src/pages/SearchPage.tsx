import { FormEvent, useEffect, useState } from "react";

import { api } from "../api";
import type { Candidate, Job, SearchRun } from "../types";

type SearchPageProps = {
  jobs: Job[];
  selectedJobId: string | null;
  onSelectJob: (jobId: string) => void;
  onCandidatesFound: (candidates: Candidate[]) => void;
};

export function SearchPage({
  jobs,
  selectedJobId,
  onSelectJob,
  onCandidatesFound
}: SearchPageProps) {
  const [query, setQuery] = useState("");
  const [limit, setLimit] = useState("10");
  const [runs, setRuns] = useState<SearchRun[]>([]);
  const [latestCandidates, setLatestCandidates] = useState<Candidate[]>([]);
  const [status, setStatus] = useState("Choose a JD and create a search run.");
  const [isSearching, setIsSearching] = useState(false);

  useEffect(() => {
    if (!selectedJobId) {
      setRuns([]);
      return;
    }
    let ignore = false;
    api
      .listSearchRuns(selectedJobId)
      .then((loadedRuns) => {
        if (!ignore) {
          setRuns(loadedRuns);
        }
      })
      .catch((error: unknown) => {
        if (!ignore) {
          setStatus(error instanceof Error ? error.message : "Unable to load search runs.");
        }
      });
    return () => {
      ignore = true;
    };
  }, [selectedJobId]);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!selectedJobId) {
      setStatus("Create or select a JD before searching.");
      return;
    }
    setIsSearching(true);
    setStatus("Running sourcing search...");
    try {
      const result = await api.createSearch({
        job_id: selectedJobId,
        query,
        params: { limit: Number(limit) || 10 }
      });
      onCandidatesFound(result.candidates);
      setLatestCandidates(result.candidates);
      setRuns((current) => [
        {
          id: result.id,
          job_id: selectedJobId,
          query,
          provider: "bright_data",
          status: result.status,
          params: { limit: Number(limit) || 10 },
          candidate_count: result.candidates.length,
          created_at: new Date().toISOString(),
          completed_at: new Date().toISOString()
        },
        ...current
      ]);
      setStatus(`Search completed with ${result.candidates.length} candidates.`);
    } catch (error) {
      setStatus(error instanceof Error ? error.message : "Unable to create search run.");
    } finally {
      setIsSearching(false);
    }
  }

  return (
    <section className="workspace-grid" aria-labelledby="search-heading">
      <div className="card card-form">
        <p className="section-kicker">Sourcing</p>
        <h2 id="search-heading">Search Runs</h2>
        <form className="stack" onSubmit={handleSubmit}>
          <label>
            JD
            <select
              value={selectedJobId ?? ""}
              onChange={(event) => onSelectJob(event.target.value)}
              required
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
          <label>
            Search query
            <textarea
              value={query}
              onChange={(event) => setQuery(event.target.value)}
              required
              rows={5}
            />
          </label>
          <label>
            Candidate limit
            <input
              min="1"
              type="number"
              value={limit}
              onChange={(event) => setLimit(event.target.value)}
            />
          </label>
          <button className="primary-action" type="submit" disabled={isSearching}>
            Create search run
          </button>
        </form>
        <p className="muted">{status}</p>
      </div>

      <div className="card">
        <p className="section-kicker">Run history</p>
        <h3>{runs.length} persisted runs</h3>
        <div className="job-list">
          {runs.map((run) => (
            <article key={run.id} className="list-row static-row">
              <strong>{run.query}</strong>
              <span>
                {run.status} · {run.candidate_count} candidates
              </span>
            </article>
          ))}
        </div>
        {latestCandidates.length > 0 ? (
          <div className="candidate-grid compact-candidates">
            {latestCandidates.map((candidate) => (
              <article key={candidate.id} className="candidate-card">
                <h3>{candidate.name}</h3>
                <p>{candidate.headline ?? "No headline captured"}</p>
              </article>
            ))}
          </div>
        ) : null}
      </div>
    </section>
  );
}

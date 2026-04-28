import { FormEvent, useEffect, useState } from "react";

import { api } from "../api";
import type { Candidate, Job, SearchRun, SearchRunDetail } from "../types";

type SearchPageProps = {
  jobs: Job[];
  selectedJobId: string | null;
  onSelectJob: (jobId: string) => void;
  onCandidatesFound: (candidates: Candidate[]) => void;
  onReviewCandidate: (candidate: Candidate) => void;
};

export function SearchPage({
  jobs,
  selectedJobId,
  onSelectJob,
  onCandidatesFound,
  onReviewCandidate
}: SearchPageProps) {
  const [query, setQuery] = useState("");
  const [limit, setLimit] = useState("10");
  const [runs, setRuns] = useState<SearchRun[]>([]);
  const [runDetails, setRunDetails] = useState<Record<string, SearchRunDetail>>({});
  const [status, setStatus] = useState("Choose a JD and create a search run.");
  const [isSearching, setIsSearching] = useState(false);
  const selectedJob = jobs.find((job) => job.id === selectedJobId) ?? null;

  useEffect(() => {
    setQuery(searchQueryForJob(selectedJob));
  }, [selectedJob]);

  useEffect(() => {
    if (!selectedJobId) {
      setRuns([]);
      setRunDetails({});
      return;
    }
    let ignore = false;
    api
      .listSearchRuns(selectedJobId)
      .then((loadedRuns) => {
        if (!ignore) {
          setRuns(loadedRuns);
          setRunDetails({});
          loadedRuns.forEach((run) => {
            api
              .getSearchRun(run.id)
              .then((detail) => {
                if (!ignore) {
                  setRunDetails((current) => ({ ...current, [run.id]: detail }));
                }
              })
              .catch(() => undefined);
          });
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
      setRunDetails((current) => ({
        ...current,
        [result.id]: {
          id: result.id,
          job_id: selectedJobId,
          query,
          provider: "bright_data",
          status: result.status,
          params: { limit: Number(limit) || 10 },
          candidate_count: result.candidates.length,
          created_at: new Date().toISOString(),
          completed_at: new Date().toISOString(),
          candidates: result.candidates
        }
      }));
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
              <RunCandidates
                candidates={runDetails[run.id]?.candidates ?? []}
                onReviewCandidate={onReviewCandidate}
              />
            </article>
          ))}
        </div>
      </div>
    </section>
  );
}

function searchQueryForJob(job: Job | null): string {
  if (job === null) {
    return "";
  }

  return job.search_notes.trim() || job.description.trim() || job.title;
}

function RunCandidates({
  candidates,
  onReviewCandidate
}: {
  candidates: Candidate[];
  onReviewCandidate: (candidate: Candidate) => void;
}) {
  if (candidates.length === 0) {
    return null;
  }

  return (
    <div className="run-candidate-list">
      {candidates.map((candidate) => (
        <button
          key={candidate.id}
          type="button"
          className="text-action run-candidate-row"
          aria-label={`Open ${candidate.name}`}
          onClick={() => onReviewCandidate(candidate)}
        >
          <strong>{candidate.name}</strong>
          <span>{candidate.headline ?? "No headline captured"}</span>
        </button>
      ))}
    </div>
  );
}

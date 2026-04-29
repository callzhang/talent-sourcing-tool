import { useEffect, useState } from "react";

import "./App.css";
import { api } from "./api";
import { CandidateDetailPage } from "./pages/CandidateDetailPage";
import { CandidatesPage } from "./pages/CandidatesPage";
import { JobsPage } from "./pages/JobsPage";
import { RefinementsPage } from "./pages/RefinementsPage";
import { SearchPage } from "./pages/SearchPage";
import type { Candidate, Job, JobWithRubric } from "./types";

type Page = "jobs" | "search" | "candidates" | "candidate-detail" | "refinements";

const pages: Array<{ id: Exclude<Page, "candidate-detail">; label: string }> = [
  { id: "jobs", label: "Jobs" },
  { id: "search", label: "Search" },
  { id: "candidates", label: "Candidates" },
  { id: "refinements", label: "Refinements" }
];

export function App() {
  const [page, setPage] = useState<Page>("jobs");
  const [jobs, setJobs] = useState<Job[]>([]);
  const [selectedJobId, setSelectedJobId] = useState<string | null>(null);
  const [candidates, setCandidates] = useState<Candidate[]>([]);
  const [selectedCandidate, setSelectedCandidate] = useState<Candidate | null>(null);

  useEffect(() => {
    let ignore = false;
    api
      .listJobs()
      .then((loadedJobs) => {
        if (ignore) {
          return;
        }
        setJobs(loadedJobs);
        if (!selectedJobId && loadedJobs[0]) {
          setSelectedJobId(loadedJobs[0].id);
        }
      })
      .catch(() => undefined);
    return () => {
      ignore = true;
    };
  }, []);

  function handleCreatedJob(jobWithRubric: JobWithRubric) {
    setJobs((currentJobs) => [
      jobWithRubric.job,
      ...currentJobs.filter((job) => job.id !== jobWithRubric.job.id)
    ]);
    setSelectedJobId(jobWithRubric.job.id);
  }

  function handleReviewCandidate(candidate: Candidate) {
    setSelectedCandidate(candidate);
    setPage("candidate-detail");
  }

  return (
    <main className="app-shell">
      <header className="app-header">
        <div className="app-nav">
          <div className="brand-lockup" aria-label="Talent Sourcing Tool">
            <span className="brand-mark" aria-hidden="true">
              TS
            </span>
            <span className="brand-name">Talent Sourcing Tool</span>
          </div>
          <nav className="tabs" aria-label="Primary">
            {pages.map((item) => (
              <button
                key={item.id}
                type="button"
                className="tab"
                aria-pressed={page === item.id}
                onClick={() => setPage(item.id)}
              >
                {item.label}
              </button>
            ))}
          </nav>
        </div>
        <div className="page-intro">
          <p className="eyebrow">Local sourcing workspace</p>
          <h1>Talent Sourcing Tool</h1>
          <p className="hero-copy">
            JD to multi-channel sourcing to AI review to pass/proceed feedback loop.
          </p>
        </div>
      </header>

      {page === "jobs" ? (
        <JobsPage
          selectedJobId={selectedJobId}
          onSelectJob={setSelectedJobId}
          onCreatedJob={handleCreatedJob}
        />
      ) : null}
      {page === "search" ? (
        <SearchPage
          jobs={jobs}
          selectedJobId={selectedJobId}
          onSelectJob={setSelectedJobId}
          onCandidatesFound={setCandidates}
          onReviewCandidate={handleReviewCandidate}
        />
      ) : null}
      {page === "candidates" ? (
        <CandidatesPage
          selectedJobId={selectedJobId}
          jobs={jobs}
          candidates={candidates}
          onSelectJob={setSelectedJobId}
          onLoadedCandidates={setCandidates}
          onReviewCandidate={handleReviewCandidate}
        />
      ) : null}
      {page === "candidate-detail" ? (
        <CandidateDetailPage
          selectedJobId={selectedJobId}
          candidate={selectedCandidate}
          onBack={() => setPage("candidates")}
        />
      ) : null}
      {page === "refinements" ? (
        <RefinementsPage
          jobs={jobs}
          selectedJobId={selectedJobId}
          onSelectJob={setSelectedJobId}
        />
      ) : null}
    </main>
  );
}

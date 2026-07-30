import { useEffect, useState } from "react";

import "./App.css";
import { api } from "./api";
import { CandidateDetailPage } from "./pages/CandidateDetailPage";
import { CandidatesPage } from "./pages/CandidatesPage";
import { JobsPage } from "./pages/JobsPage";
import { RefinementsPage } from "./pages/RefinementsPage";
import { SearchPage } from "./pages/SearchPage";
import type { Candidate, Job, JobWithRubric, SystemStatus } from "./types";

type Page = "jobs" | "search" | "candidates" | "candidate-detail" | "refinements";

const pages: Array<{ id: Exclude<Page, "candidate-detail">; label: string }> = [
  { id: "jobs", label: "岗位" },
  { id: "search", label: "搜索" },
  { id: "candidates", label: "候选人" },
  { id: "refinements", label: "岗位优化" }
];

export function App() {
  const [page, setPage] = useState<Page>("jobs");
  const [jobs, setJobs] = useState<Job[]>([]);
  const [selectedJobId, setSelectedJobId] = useState<string | null>(null);
  const [candidates, setCandidates] = useState<Candidate[]>([]);
  const [selectedCandidate, setSelectedCandidate] = useState<Candidate | null>(null);
  const [systemStatus, setSystemStatus] = useState<SystemStatus | null>(null);

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

  useEffect(() => {
    let ignore = false;
    api
      .getSystemStatus()
      .then((status) => {
        if (!ignore) {
          setSystemStatus(status);
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
          <div className="brand-lockup" aria-label="人才搜索与评估">
            <span className="brand-mark" aria-hidden="true">
              TS
            </span>
            <span className="brand-name">人才搜索与评估</span>
          </div>
          <nav className="tabs" aria-label="主导航">
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
        <div className="workspace-context">
          <h1>人才搜索与评估</h1>
        </div>
      </header>

      {page === "jobs" ? (
        <JobsPage
          selectedJobId={selectedJobId}
          systemStatus={systemStatus}
          onSelectJob={setSelectedJobId}
          onCreatedJob={handleCreatedJob}
        />
      ) : null}
      {page === "search" ? (
        <SearchPage
          jobs={jobs}
          selectedJobId={selectedJobId}
          systemStatus={systemStatus}
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
          systemStatus={systemStatus}
          onSelectJob={setSelectedJobId}
          onLoadedCandidates={setCandidates}
          onReviewCandidate={handleReviewCandidate}
        />
      ) : null}
      {page === "candidate-detail" ? (
        <CandidateDetailPage
          selectedJobId={selectedJobId}
          candidate={selectedCandidate}
          systemStatus={systemStatus}
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

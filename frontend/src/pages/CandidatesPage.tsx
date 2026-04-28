import { useEffect, useMemo, useState } from "react";

import { api } from "../api";
import type { Candidate, Job } from "../types";

type CandidatesPageProps = {
  selectedJobId: string | null;
  jobs: Job[];
  candidates: Candidate[];
  onSelectJob: (jobId: string) => void;
  onLoadedCandidates: (candidates: Candidate[]) => void;
  onReviewCandidate: (candidate: Candidate) => void;
};

export function CandidatesPage({
  selectedJobId,
  jobs,
  candidates,
  onSelectJob,
  onLoadedCandidates,
  onReviewCandidate
}: CandidatesPageProps) {
  const [status, setStatus] = useState("Loading searched candidates...");
  const [activeCandidateId, setActiveCandidateId] = useState<string | null>(null);

  const activeCandidate = useMemo(() => {
    return (
      candidates.find((candidate) => candidate.id === activeCandidateId) ??
      candidates[0] ??
      null
    );
  }, [activeCandidateId, candidates]);

  useEffect(() => {
    if (!selectedJobId) {
      setStatus("Select a JD before reviewing candidates.");
      return;
    }
    let ignore = false;
    api
      .listCandidates(selectedJobId)
      .then(async (loadedCandidates) => {
        if (ignore) {
          return;
        }
        onLoadedCandidates(loadedCandidates);
        setActiveCandidateId((currentCandidateId) => {
          if (loadedCandidates.some((candidate) => candidate.id === currentCandidateId)) {
            return currentCandidateId;
          }
          return loadedCandidates[0]?.id ?? null;
        });
        setStatus(
          loadedCandidates.length > 0
            ? "Review candidates from completed search runs."
            : "No searched candidates for this JD yet."
        );
        if (loadedCandidates.length === 0 && jobs.length > 1) {
          await selectLatestCandidateJob(selectedJobId, jobs, onSelectJob, () => ignore);
        }
      })
      .catch((error: unknown) => {
        if (!ignore) {
          setStatus(error instanceof Error ? error.message : "Unable to load candidates.");
        }
      });
    return () => {
      ignore = true;
    };
  }, [jobs, onLoadedCandidates, onSelectJob, selectedJobId]);

  return (
    <div className="candidates-grid">
      <section className="card candidate-list-pane" aria-label="Candidate listings">
        <p className="section-kicker">Candidate review queue</p>
        <h2 id="candidates-heading">Candidates</h2>
        {jobs.length > 0 ? (
          <label className="compact-field">
            Review queue JD
            <select
              value={selectedJobId ?? ""}
              onChange={(event) => onSelectJob(event.target.value)}
            >
              {jobs.map((job) => (
                <option key={job.id} value={job.id}>
                  {job.title}
                </option>
              ))}
            </select>
          </label>
        ) : null}
        <p className="muted">{status}</p>
        <div className="candidate-list">
          {candidates.map((candidate) => (
            <button
              key={candidate.id}
              type="button"
              className="list-row candidate-list-row"
              aria-pressed={candidate.id === activeCandidate?.id}
              onClick={() => setActiveCandidateId(candidate.id)}
            >
              <strong>{candidate.name}</strong>
              <span>{candidate.headline ?? "No headline captured"}</span>
              <span>{[candidate.current_company, candidate.location].filter(Boolean).join(" · ")}</span>
            </button>
          ))}
        </div>
      </section>

      <section className="card candidate-detail-pane" aria-label="Candidate detail">
        <p className="section-kicker">Selected candidate</p>
        <CandidateDetail candidate={activeCandidate} onReviewCandidate={onReviewCandidate} />
      </section>
    </div>
  );
}

async function selectLatestCandidateJob(
  selectedJobId: string,
  jobs: Job[],
  onSelectJob: (jobId: string) => void,
  isIgnored: () => boolean
) {
  try {
    const latestCandidates = await api.listCandidates();
    const latestCandidate = latestCandidates.find((candidate) => candidate.last_search_run_id);
    if (isIgnored() || !latestCandidate?.last_search_run_id) {
      return;
    }
    const latestSearchRun = await api.getSearchRun(latestCandidate.last_search_run_id);
    if (
      !isIgnored() &&
      latestSearchRun.job_id !== selectedJobId &&
      jobs.some((job) => job.id === latestSearchRun.job_id)
    ) {
      onSelectJob(latestSearchRun.job_id);
    }
  } catch {
    return;
  }
}

function CandidateDetail({
  candidate,
  onReviewCandidate
}: {
  candidate: Candidate | null;
  onReviewCandidate: (candidate: Candidate) => void;
}) {
  if (candidate === null) {
    return <p className="empty-state">Select a candidate to inspect sourcing evidence.</p>;
  }

  const raw = rawProfile(candidate);
  const signals = stringList(raw.signals);
  const risks = stringList(raw.risks);
  const sources = sourceList(raw.sources);

  return (
    <div className="candidate-detail">
      <div className="split-heading">
        <h3>{candidate.name}</h3>
        <span>{candidate.last_search_rank ? `Rank ${candidate.last_search_rank}` : "Sourced"}</span>
      </div>
      <p>{candidate.headline ?? "No headline captured"}</p>
      <p className="muted">
        {[candidate.current_company, candidate.location].filter(Boolean).join(" · ")}
      </p>
      <a href={candidate.linkedin_url} target="_blank" rel="noreferrer">
        LinkedIn profile
      </a>
      <EvidenceList label="Signals" items={signals} />
      <EvidenceList label="Risks" items={risks} />
      {sources.length > 0 ? (
        <div>
          <p className="detail-label">Sources</p>
          <div className="source-list">
            {sources.map((source) => (
              <a key={source.url} href={source.url} target="_blank" rel="noreferrer">
                {source.title}
              </a>
            ))}
          </div>
        </div>
      ) : null}
      <button
        type="button"
        className="secondary-action"
        onClick={() => onReviewCandidate(candidate)}
      >
        Review {candidate.name}
      </button>
    </div>
  );
}

function EvidenceList({ label, items }: { label: string; items: string[] }) {
  if (items.length === 0) {
    return null;
  }

  return (
    <div>
      <p className="detail-label">{label}</p>
      <ul className="compact-list">
        {items.map((item) => (
          <li key={item}>{item}</li>
        ))}
      </ul>
    </div>
  );
}

function rawProfile(candidate: Candidate): Record<string, unknown> {
  const raw = candidate.profile_data.raw;
  if (typeof raw === "object" && raw !== null && !Array.isArray(raw)) {
    return raw as Record<string, unknown>;
  }
  return {};
}

function stringList(value: unknown): string[] {
  if (!Array.isArray(value)) {
    return [];
  }
  return value.filter((item): item is string => typeof item === "string" && item.length > 0);
}

function sourceList(value: unknown): Array<{ title: string; url: string }> {
  if (!Array.isArray(value)) {
    return [];
  }
  return value.flatMap((item) => {
    if (typeof item !== "object" || item === null || Array.isArray(item)) {
      return [];
    }
    const source = item as Record<string, unknown>;
    const title = typeof source.title === "string" ? source.title : null;
    const url = typeof source.url === "string" ? source.url : null;
    const sourceType =
      typeof source.source_type === "string"
        ? source.source_type
        : typeof source.channel === "string"
          ? source.channel
          : inferSourceType(url);
    return title && url
      ? [{ title: formatSourceLabel(sourceType, title), url }]
      : [];
  });
}

function inferSourceType(url: string | null): string {
  if (!url) {
    return "source";
  }
  if (url.includes("linkedin.com")) {
    return "linkedin";
  }
  if (url.includes("github.com")) {
    return "github";
  }
  if (url.includes("openreview.net")) {
    return "openreview";
  }
  if (url.includes("arxiv.org")) {
    return "arxiv";
  }
  if (url.includes("exa.ai")) {
    return "exa";
  }
  if (url.includes("brightdata.com")) {
    return "brightdata_discover";
  }
  return "source";
}

function formatSourceLabel(sourceType: string, title: string): string {
  const labels: Record<string, string> = {
    linkedin: "LinkedIn",
    github: "GitHub",
    openreview: "OpenReview",
    arxiv: "arXiv",
    exa: "Exa",
    brightdata_discover: "Bright Data Discover",
    source: "Source"
  };
  return `${labels[sourceType] ?? sourceType}: ${title}`;
}

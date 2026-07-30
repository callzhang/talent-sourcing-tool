import { useEffect, useState } from "react";

import "./App.css";
import { api } from "./api";
import { CandidateDetailPage } from "./pages/CandidateDetailPage";
import { CandidatesPage } from "./pages/CandidatesPage";
import { JobsPage } from "./pages/JobsPage";
import { RefinementsPage } from "./pages/RefinementsPage";
import { SearchPage } from "./pages/SearchPage";
import type { Candidate, Job, JobWithRubric, ProviderChecks, SystemStatus } from "./types";

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
  const [systemStatus, setSystemStatus] = useState<SystemStatus | null>(null);
  const [providerChecks, setProviderChecks] = useState<ProviderChecks | null>(null);

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

  useEffect(() => {
    let ignore = false;
    api
      .getProviderChecks()
      .then((checks) => {
        if (!ignore && isProviderChecks(checks)) {
          setProviderChecks(checks);
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

  const workspaceLabel =
    systemStatus?.environment === "vercel"
      ? "Production sourcing workspace"
      : "Local sourcing workspace";

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
          <p className="eyebrow">{workspaceLabel}</p>
          <h1>Talent Sourcing Tool</h1>
          <p className="hero-copy">
            JD to multi-channel sourcing to AI review to pass/proceed feedback loop.
          </p>
        </div>
        {systemStatus &&
        (systemStatus.warnings.length > 0 ||
          (systemStatus.hard_blockers?.length ?? 0) > 0 ||
          (systemStatus.optional_degradations?.length ?? 0) > 0) ? (
          <section className="status-banner" aria-label="System warnings">
            <strong>
              {systemStatus.environment === "vercel"
                ? "Deployment configuration warnings"
                : "Environment warnings"}
            </strong>
            {systemStatus.warnings.length > 0 ? (
              <ul>
                {systemStatus.warnings.map((warning) => (
                  <li key={warning}>{warning}</li>
                ))}
              </ul>
            ) : null}
            {systemStatus.hard_blockers && systemStatus.hard_blockers.length > 0 ? (
              <div className="status-detail-group">
                <strong>Hard blockers</strong>
                <ul>
                  {systemStatus.hard_blockers.map((blocker) => (
                    <li key={blocker.code}>
                      {blocker.message}
                      {blocker.env_vars && blocker.env_vars.length > 0
                        ? ` Missing vars: ${blocker.env_vars.join(", ")}`
                        : ""}
                    </li>
                  ))}
                </ul>
              </div>
            ) : null}
            {systemStatus.optional_degradations && systemStatus.optional_degradations.length > 0 ? (
              <div className="status-detail-group">
                <strong>Optional degradations</strong>
                <ul>
                  {systemStatus.optional_degradations.map((degradation) => (
                    <li key={degradation.code}>
                      {degradation.message}
                      {degradation.env_vars && degradation.env_vars.length > 0
                        ? ` Missing vars: ${degradation.env_vars.join(", ")}`
                        : ""}
                    </li>
                  ))}
                </ul>
              </div>
            ) : null}
          </section>
        ) : null}
        {systemStatus ? (
          <DeploymentReadinessPanel
            systemStatus={systemStatus}
            providerChecks={providerChecks}
          />
        ) : null}
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

function DeploymentReadinessPanel({
  systemStatus,
  providerChecks
}: {
  systemStatus: SystemStatus;
  providerChecks: ProviderChecks | null;
}) {
  const channelLabels: Record<string, string> = {
    linkedin: "LinkedIn",
    github: "GitHub",
    openreview: "OpenReview",
    arxiv: "arXiv",
    exa: "Exa",
    brightdata_discover: "Bright Data Discover"
  };
  const channelAvailability = systemStatus.capabilities.channel_availability;
  const requiredChannels =
    systemStatus.capabilities.required_channels ??
    (channelAvailability
      ? (Object.keys(channelAvailability).filter(
          (channel) => !["github", "openreview", "arxiv"].includes(channel)
        ) as Array<keyof typeof channelAvailability & string>)
      : []);
  const optionalChannels = systemStatus.capabilities.optional_channels ?? [];
  const missingEnvVars = systemStatus.capabilities.missing_env_vars;
  const sourcingReady =
    channelAvailability === undefined
      ? systemStatus.capabilities.exa_configured || systemStatus.capabilities.brightdata_configured
      : requiredChannels.every((channel) => channelAvailability[channel as keyof typeof channelAvailability]);
  const missingRequiredChannelVars = new Set<string>(
    requiredChannels
      .flatMap((channel) => missingEnvVars?.channels?.[channel as keyof typeof missingEnvVars.channels] ?? [])
      .filter((value) => value.length > 0)
  );
  const missingOptionalChannelVars = new Set<string>(
    optionalChannels
      .flatMap((channel) => missingEnvVars?.channels?.[channel] ?? [])
      .filter((value) => value.length > 0)
  );
  const unavailableOptionalChannels = optionalChannels.filter(
    (channel) => channelAvailability?.[channel] === false
  );
  const readinessItems = [
    {
      label: "Storage",
      ready: systemStatus.capabilities.persistent_storage_configured,
      detail: systemStatus.capabilities.persistent_storage_configured
        ? "Durable database configured"
        : formatMissingVars(missingEnvVars?.storage, "Needs DATABASE_URL or TALENT_DATABASE_URL")
    },
    {
      label: "AI review",
      ready: systemStatus.capabilities.review_configured,
      detail: systemStatus.capabilities.review_configured
        ? `Provider: ${systemStatus.capabilities.review_provider}`
        : formatMissingVars(missingEnvVars?.review, "Needs TALENT_OPENAI_API_KEY")
    },
    {
      label: "Channel coverage",
      ready: sourcingReady,
      detail: sourcingReady
        ? missingOptionalChannelVars.size > 0
          ? `Required sourcing channels are available. Optional: ${[...missingOptionalChannelVars].join(", ")}`
          : "Required sourcing channels are available"
        : formatMissingVars(
            [...missingRequiredChannelVars],
            `Missing required channel coverage: ${requiredChannels
              .map((channel) => channelLabels[channel] ?? channel)
              .join(", ")}`
          ),
      diagnostics: channelDiagnostics(providerChecks, unavailableOptionalChannels, channelLabels)
    }
  ];

  return (
    <section className="readiness-panel" aria-label="Deployment readiness">
      <div className="split-heading">
        <strong>Deployment readiness</strong>
        <span
          className={`status-pill ${
            systemStatus.deployment_ready ? "status-pill-success" : "status-pill-warning"
          }`}
        >
          {systemStatus.deployment_ready ? "Ready" : "Blocked"}
        </span>
      </div>
      <div className="readiness-grid">
        {readinessItems.map((item) => (
          <div key={item.label} className="readiness-item">
            <div className="split-heading">
              <span>{item.label}</span>
              <span
                className={`status-pill ${
                  item.ready ? "status-pill-success" : "status-pill-warning"
                }`}
              >
                {item.ready ? "Ready" : "Missing"}
              </span>
            </div>
            <p className="muted">{item.detail}</p>
            {"diagnostics" in item && item.diagnostics ? (
              <p className="muted readiness-diagnostic">{item.diagnostics}</p>
            ) : null}
          </div>
        ))}
      </div>
      {systemStatus.delivery_resources ? (
        <section className="handoff-panel" aria-label="Delivery handoff">
          <div className="split-heading">
            <strong>Delivery handoff</strong>
            <span className="status-pill status-pill-neutral">Operator checklist</span>
          </div>
          <div className="handoff-grid">
            <div className="readiness-item">
              <span>Production site</span>
              <a href={systemStatus.delivery_resources.production_url} target="_blank" rel="noreferrer">
                {systemStatus.delivery_resources.production_url}
              </a>
              <p className="muted">Share this URL with HR for live validation.</p>
            </div>
            <div className="readiness-item">
              <span>Local app</span>
              <a href={systemStatus.delivery_resources.local_url} target="_blank" rel="noreferrer">
                {systemStatus.delivery_resources.local_url}
              </a>
              <p className="muted">Use this during local HR flow rehearsal.</p>
            </div>
            <div className="readiness-item">
              <span>Owner checklist</span>
              <code>{systemStatus.delivery_resources.owner_checklist_path}</code>
              <p className="muted">Shortest handoff doc for DB URL and OpenAI key ownership.</p>
            </div>
            <div className="readiness-item">
              <span>Runbook</span>
              <code>{systemStatus.delivery_resources.runbook_path}</code>
              <p className="muted">Full production procedure and verification notes.</p>
            </div>
          </div>
          <div className="handoff-actions">
            <div>
              <strong>Verify in order</strong>
              <ol className="command-list">
                {systemStatus.delivery_resources.verification_commands.map((command) => (
                  <li key={command}>
                    <code>{command}</code>
                  </li>
                ))}
              </ol>
            </div>
            <div>
              <strong>Owner confirmations needed</strong>
              <ul className="owner-prompt-list">
                {systemStatus.delivery_resources.owner_prompts.map((prompt) => (
                  <li key={prompt}>{prompt}</li>
                ))}
              </ul>
            </div>
          </div>
        </section>
      ) : null}
    </section>
  );
}

function formatMissingVars(vars: string[] | undefined, fallback: string): string {
  if (!vars || vars.length === 0) {
    return fallback;
  }
  return `Missing: ${vars.join(", ")}`;
}

function channelDiagnostics(
  providerChecks: ProviderChecks | null,
  unavailableOptionalChannels: string[],
  channelLabels: Record<string, string>
): string | null {
  const diagnostics: string[] = [];
  if (unavailableOptionalChannels.length > 0) {
    diagnostics.push(
      `Optional channel unavailable: ${unavailableOptionalChannels
        .map((channel) => channelLabels[channel] ?? channel)
        .join(", ")}`
    );
  }
  if (providerChecks) {
    const exa = providerChecks.providers.exa;
    const brightdata = providerChecks.providers.brightdata;
    if (exa.status !== "ok" && exa.detail) {
      diagnostics.push(`Exa: ${exa.detail}`);
    }
    if (brightdata.status !== "ok" && brightdata.detail) {
      diagnostics.push(`Bright Data: ${brightdata.detail}`);
    }
    if (brightdata.active_zones && brightdata.active_zones.length > 0) {
      diagnostics.push(`Active zones: ${brightdata.active_zones.join(", ")}`);
    }
  }
  return diagnostics.length > 0 ? diagnostics.join(" ") : null;
}

function isProviderChecks(value: unknown): value is ProviderChecks {
  if (typeof value !== "object" || value === null || Array.isArray(value)) {
    return false;
  }
  const providers = (value as { providers?: unknown }).providers;
  if (typeof providers !== "object" || providers === null || Array.isArray(providers)) {
    return false;
  }
  const exa = (providers as { exa?: unknown }).exa;
  const brightdata = (providers as { brightdata?: unknown }).brightdata;
  return (
    typeof exa === "object" &&
    exa !== null &&
    !Array.isArray(exa) &&
    typeof brightdata === "object" &&
    brightdata !== null &&
    !Array.isArray(brightdata)
  );
}

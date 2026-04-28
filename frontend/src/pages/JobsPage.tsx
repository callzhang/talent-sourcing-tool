import { FormEvent, useEffect, useState } from "react";

import { api } from "../api";
import type { Job, JobWithRubric, SearchChannel } from "../types";

const SEARCH_CHANNEL_OPTIONS: Array<{ value: SearchChannel; label: string }> = [
  { value: "linkedin", label: "LinkedIn" },
  { value: "github", label: "GitHub" },
  { value: "openreview", label: "OpenReview" },
  { value: "arxiv", label: "arXiv" },
  { value: "exa", label: "Exa" }
];

type JobsPageProps = {
  selectedJobId: string | null;
  onSelectJob: (jobId: string) => void;
  onCreatedJob: (job: JobWithRubric) => void;
};

export function JobsPage({ selectedJobId, onSelectJob, onCreatedJob }: JobsPageProps) {
  const [jobs, setJobs] = useState<Job[]>([]);
  const [activeJob, setActiveJob] = useState<JobWithRubric | null>(null);
  const [title, setTitle] = useState("");
  const [description, setDescription] = useState("");
  const [targetProfile, setTargetProfile] = useState("");
  const [redFlags, setRedFlags] = useState("");
  const [searchNotes, setSearchNotes] = useState("");
  const [searchChannels, setSearchChannels] = useState<SearchChannel[]>(["linkedin", "github", "exa"]);
  const [status, setStatus] = useState("Loading jobs...");
  const [isSaving, setIsSaving] = useState(false);

  useEffect(() => {
    let ignore = false;
    api
      .listJobs()
      .then((loadedJobs) => {
        if (ignore) {
          return;
        }
        setJobs(loadedJobs);
        setStatus(loadedJobs.length > 0 ? "Select a JD to inspect its rubric." : "No JDs yet.");
        if (!selectedJobId && loadedJobs[0]) {
          onSelectJob(loadedJobs[0].id);
        }
      })
      .catch((error: unknown) => {
        if (!ignore) {
          setStatus(error instanceof Error ? error.message : "Unable to load jobs.");
        }
      });
    return () => {
      ignore = true;
    };
  }, [onSelectJob, selectedJobId]);

  useEffect(() => {
    if (!selectedJobId) {
      setActiveJob(null);
      return;
    }
    let ignore = false;
    api
      .getJob(selectedJobId)
      .then((job) => {
        if (!ignore) {
          setActiveJob(job);
        }
      })
      .catch((error: unknown) => {
        if (!ignore) {
          setStatus(error instanceof Error ? error.message : "Unable to load rubric.");
        }
      });
    return () => {
      ignore = true;
    };
  }, [selectedJobId]);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setIsSaving(true);
    setStatus("Generating rubric...");
    try {
      const created = await api.createJob({
        title,
        description,
        target_profile_text: targetProfile,
        red_flags_text: redFlags,
        search_notes: searchNotes,
        search_channels: searchChannels
      });
      setJobs((current) => [created.job, ...current.filter((job) => job.id !== created.job.id)]);
      setActiveJob(created);
      onCreatedJob(created);
      setTitle("");
      setDescription("");
      setTargetProfile("");
      setRedFlags("");
      setSearchNotes("");
      setSearchChannels(["linkedin", "github", "exa"]);
      setStatus("JD created and rubric generated.");
    } catch (error) {
      setStatus(error instanceof Error ? error.message : "Unable to create JD.");
    } finally {
      setIsSaving(false);
    }
  }

  return (
    <div className="jobs-grid">
      <section className="card job-list-pane" aria-label="Job listings">
        <p className="section-kicker">Jobs</p>
        <h2 id="jobs-heading">Job listings</h2>
        <p className="muted">{status}</p>
        <div className="job-list">
          {jobs.map((job) => (
            <button
              key={job.id}
              type="button"
              className="list-row"
              aria-pressed={job.id === selectedJobId}
              onClick={() => onSelectJob(job.id)}
            >
              <strong>{job.title}</strong>
            </button>
          ))}
        </div>
      </section>

      <section className="card job-detail-pane" aria-label="Job detail">
        <p className="section-kicker">Active rubric</p>
        <div className="split-heading">
          <h3>{activeJob?.job.title ?? "No JD selected"}</h3>
          <span>{activeJob ? `v${activeJob.rubric.version}` : "Draft"}</span>
        </div>
        <JobDetail job={activeJob} />
        <RubricPreview job={activeJob} />
        <section className="create-job-panel" aria-labelledby="create-job-heading">
          <p className="section-kicker">JD intake</p>
          <h2 id="create-job-heading">JD Management</h2>
          <form className="stack" onSubmit={handleSubmit}>
            <label>
              JD title
              <input value={title} onChange={(event) => setTitle(event.target.value)} required />
            </label>
            <label>
              JD description
              <textarea
                value={description}
                onChange={(event) => setDescription(event.target.value)}
                required
                rows={5}
              />
            </label>
            <label>
              Target profile
              <textarea
                value={targetProfile}
                onChange={(event) => setTargetProfile(event.target.value)}
              />
            </label>
            <label>
              Red flags
              <textarea value={redFlags} onChange={(event) => setRedFlags(event.target.value)} />
            </label>
            <label>
              Search notes
              <textarea
                value={searchNotes}
                onChange={(event) => setSearchNotes(event.target.value)}
              />
            </label>
            <SearchChannelField value={searchChannels} onChange={setSearchChannels} />
            <button className="primary-action" type="submit" disabled={isSaving}>
              Create JD and rubric
            </button>
          </form>
        </section>
      </section>
    </div>
  );
}

function JobDetail({ job }: { job: JobWithRubric | null }) {
  if (job === null) {
    return null;
  }

  return (
    <div className="job-detail">
      <DetailBlock label="JD description" value={job.job.description} />
      <DetailBlock label="Target profile" value={job.job.target_profile_text} />
      <DetailBlock label="Red flags" value={job.job.red_flags_text} />
      <DetailBlock label="Search notes" value={job.job.search_notes} />
      <DetailBlock label="Search channels" value={job.job.search_channels.map(channelLabel).join(", ")} />
    </div>
  );
}

function DetailBlock({ label, value }: { label: string; value: string }) {
  if (!value.trim()) {
    return null;
  }

  return (
    <section className="detail-block" aria-label={label}>
      <p className="detail-label">{label}</p>
      <p>{value}</p>
    </section>
  );
}

function RubricPreview({ job }: { job: JobWithRubric | null }) {
  if (job === null) {
    return <p className="empty-state">Create or select a JD to see rubric dimensions.</p>;
  }

  return (
    <div className="rubric-list">
      {job.rubric.rubric.dimensions.map((dimension) => (
        <article key={dimension.name} className="rubric-item">
          <strong>{dimension.name}</strong>
          {dimension.weight !== undefined ? <span>{dimension.weight}%</span> : null}
          {dimension.description ? <p>{dimension.description}</p> : null}
          {dimension.scoring_guidance ? <p>{dimension.scoring_guidance}</p> : null}
          {dimension.signals && dimension.signals.length > 0 ? (
            <EvidenceList label="Signals" items={dimension.signals} />
          ) : null}
          {dimension.red_flags && dimension.red_flags.length > 0 ? (
            <EvidenceList label="Red flags" items={dimension.red_flags} />
          ) : null}
        </article>
      ))}
    </div>
  );
}

function EvidenceList({ label, items }: { label: string; items: string[] }) {
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

function SearchChannelField({
  value,
  onChange
}: {
  value: SearchChannel[];
  onChange: (channels: SearchChannel[]) => void;
}) {
  return (
    <fieldset className="channel-fieldset">
      <legend>Search channels</legend>
      <div className="channel-option-list">
        {SEARCH_CHANNEL_OPTIONS.map((channel) => (
          <label key={channel.value} className="checkbox-row">
            <input
              type="checkbox"
              checked={value.includes(channel.value)}
              onChange={() => onChange(toggleChannel(value, channel.value))}
            />
            <span>{channel.label}</span>
          </label>
        ))}
      </div>
    </fieldset>
  );
}

function toggleChannel(current: SearchChannel[], channel: SearchChannel): SearchChannel[] {
  if (current.includes(channel)) {
    return current.filter((value) => value !== channel);
  }
  return SEARCH_CHANNEL_OPTIONS.map((option) => option.value).filter(
    (value) => value === channel || current.includes(value)
  );
}

function channelLabel(channel: string): string {
  return SEARCH_CHANNEL_OPTIONS.find((option) => option.value === channel)?.label ?? channel;
}

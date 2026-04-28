import { FormEvent, useEffect, useState } from "react";

import { api } from "../api";
import type { Job, JobWithRubric } from "../types";

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
        search_notes: searchNotes
      });
      setJobs((current) => [created.job, ...current.filter((job) => job.id !== created.job.id)]);
      setActiveJob(created);
      onCreatedJob(created);
      setTitle("");
      setDescription("");
      setTargetProfile("");
      setRedFlags("");
      setSearchNotes("");
      setStatus("JD created and rubric generated.");
    } catch (error) {
      setStatus(error instanceof Error ? error.message : "Unable to create JD.");
    } finally {
      setIsSaving(false);
    }
  }

  return (
    <section className="workspace-grid" aria-labelledby="jobs-heading">
      <div className="card card-form">
        <p className="section-kicker">JD intake</p>
        <h2 id="jobs-heading">JD Management</h2>
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
            <textarea value={targetProfile} onChange={(event) => setTargetProfile(event.target.value)} />
          </label>
          <label>
            Red flags
            <textarea value={redFlags} onChange={(event) => setRedFlags(event.target.value)} />
          </label>
          <label>
            Search notes
            <textarea value={searchNotes} onChange={(event) => setSearchNotes(event.target.value)} />
          </label>
          <button className="primary-action" type="submit" disabled={isSaving}>
            Create JD and rubric
          </button>
        </form>
        <p className="muted">{status}</p>
      </div>

      <div className="card">
        <p className="section-kicker">Active rubric</p>
        <div className="split-heading">
          <h3>{activeJob?.job.title ?? "No JD selected"}</h3>
          <span>{activeJob ? `v${activeJob.rubric.version}` : "Draft"}</span>
        </div>
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
              <span>{job.status}</span>
            </button>
          ))}
        </div>
        <RubricPreview job={activeJob} />
      </div>
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
          {dimension.scoring_guidance ? <p>{dimension.scoring_guidance}</p> : null}
        </article>
      ))}
    </div>
  );
}

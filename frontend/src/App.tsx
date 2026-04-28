import { useState } from "react";

import "./App.css";

type Page = "jobs" | "search" | "candidates" | "refinements";

const pages: Array<{ id: Page; label: string; title: string; description: string }> = [
  {
    id: "jobs",
    label: "Jobs",
    title: "JD Management",
    description: "Create job descriptions and review generated rubric structure."
  },
  {
    id: "search",
    label: "Search",
    title: "Search Runs",
    description: "Prepare Bright Data search queries against the selected JD."
  },
  {
    id: "candidates",
    label: "Candidates",
    title: "Candidates",
    description: "Review sourced LinkedIn profiles and queue deep AI reviews."
  },
  {
    id: "refinements",
    label: "Refinements",
    title: "Refinement Suggestions",
    description: "Use pass reasons and proceed signals to improve sourcing."
  }
];

export function App() {
  const [page, setPage] = useState<Page>("jobs");
  const activePage = pages.find((item) => item.id === page) ?? pages[0];

  return (
    <main className="app-shell">
      <header className="hero">
        <div>
          <p className="eyebrow">Local sourcing workspace</p>
          <h1>Talent Sourcing Tool</h1>
          <p className="hero-copy">
            JD to LinkedIn sourcing to AI review to pass/proceed feedback loop.
          </p>
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
      </header>

      <section className="panel" aria-labelledby={`${activePage.id}-heading`}>
        <div>
          <p className="panel-kicker">Task workspace</p>
          <h2 id={`${activePage.id}-heading`}>{activePage.title}</h2>
          <p>{activePage.description}</p>
        </div>
        <div className="panel-note">
          Later tasks can replace this placeholder with the dedicated page component without changing
          the shell navigation contract.
        </div>
      </section>
    </main>
  );
}

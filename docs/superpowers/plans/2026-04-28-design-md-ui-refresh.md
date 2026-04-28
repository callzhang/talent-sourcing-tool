# DESIGN.md UI Refresh Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Restyle the existing Talent Sourcing Tool frontend to match `DESIGN.md` using the approved Editorial Ops direction without changing product behavior.

**Architecture:** This is a presentation-only refresh. Keep the existing React page/state structure and API client unchanged, replace the global visual system in `frontend/src/App.css`, and make the smallest necessary shell markup adjustment in `frontend/src/App.tsx` for sticky navigation plus compact page intro.

**Tech Stack:** React 19, Vite 6, TypeScript, plain CSS, Vitest, Testing Library.

---

## File Structure

- Modify `frontend/src/App.css`: own the design tokens, font imports, global typography, shell, navigation, card, form, list, chip, grid, hover, focus, and responsive styling.
- Modify `frontend/src/App.tsx`: change only the header/shell markup needed to support the sticky nav and compact intro while preserving page state and callbacks.
- Modify `frontend/src/App.test.tsx`: update assertions if the shell text hierarchy changes enough to require test wording adjustments.
- Do not modify backend files, API files, page behavior, or data models.

## Task 1: Add a Shell Regression Test

**Files:**
- Modify: `frontend/src/App.test.tsx`
- Test: `frontend/src/App.test.tsx`

- [ ] **Step 1: Read the existing shell test**

Run:

```bash
sed -n '1,220p' frontend/src/App.test.tsx
```

Expected: see the current app render tests and identify where to assert the shell still exposes the app title and primary navigation.

- [ ] **Step 2: Add a shell structure assertion**

In `frontend/src/App.test.tsx`, ensure the default render test contains these checks:

```tsx
expect(screen.getByRole("banner")).toBeInTheDocument();
expect(screen.getByRole("navigation", { name: "Primary" })).toBeInTheDocument();
expect(screen.getByRole("heading", { name: "Talent Sourcing Tool" })).toBeInTheDocument();
expect(screen.getByRole("button", { name: "Jobs" })).toHaveAttribute("aria-pressed", "true");
```

If no default render test exists, add one:

```tsx
it("renders the application shell", async () => {
  render(<App />);

  expect(screen.getByRole("banner")).toBeInTheDocument();
  expect(screen.getByRole("navigation", { name: "Primary" })).toBeInTheDocument();
  expect(screen.getByRole("heading", { name: "Talent Sourcing Tool" })).toBeInTheDocument();
  expect(screen.getByRole("button", { name: "Jobs" })).toHaveAttribute("aria-pressed", "true");
});
```

- [ ] **Step 3: Run the focused test**

Run:

```bash
cd frontend && npm run test -- App.test.tsx
```

Expected: the test may pass before implementation if current semantics already satisfy it. That is acceptable because this task protects against breaking the shell during markup changes.

- [ ] **Step 4: Commit the test**

Run:

```bash
git add frontend/src/App.test.tsx
git commit -m "test: cover app shell navigation"
```

Expected: commit succeeds if the file changed. If the existing tests already had equivalent assertions and no file changed, skip the commit and note that coverage already existed.

## Task 2: Update the App Shell Markup

**Files:**
- Modify: `frontend/src/App.tsx`
- Test: `frontend/src/App.test.tsx`

- [ ] **Step 1: Replace the current hero header markup**

In `frontend/src/App.tsx`, replace the current `<header className="hero">...</header>` block with this structure:

```tsx
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
      JD to LinkedIn sourcing to AI review to pass/proceed feedback loop.
    </p>
  </div>
</header>
```

Do not change the `pages` array, page state, or conditional page rendering.

- [ ] **Step 2: Run the focused shell test**

Run:

```bash
cd frontend && npm run test -- App.test.tsx
```

Expected: PASS. If it fails due to multiple title matches, make the test target the heading specifically:

```tsx
expect(screen.getByRole("heading", { level: 1, name: "Talent Sourcing Tool" })).toBeInTheDocument();
```

- [ ] **Step 3: Commit the shell markup**

Run:

```bash
git add frontend/src/App.tsx frontend/src/App.test.tsx
git commit -m "refactor: prepare app shell for design refresh"
```

Expected: commit includes only the shell markup and any required test update.

## Task 3: Replace the Global CSS Visual System

**Files:**
- Modify: `frontend/src/App.css`
- Test: frontend test suite and visual browser check

- [ ] **Step 1: Replace font and token definitions**

At the top of `frontend/src/App.css`, replace the current `:root` and global background styling with:

```css
@import url("https://api.fontshare.com/v2/css?f[]=general-sans@600,700&display=swap");
@import url("https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;700&family=JetBrains+Mono:wght@400;500;700&display=swap");

:root {
  --color-primary: #6366f1;
  --color-primary-hover: #4f46e5;
  --color-secondary: #20970b;
  --color-neutral: #9c9c9c;
  --color-background: #fafafa;
  --color-surface: #ffffff;
  --color-text: #0a0a0a;
  --color-text-secondary: #6b6b6b;
  --color-border: #e8e8ec;
  --color-success: #10b981;
  --color-warning: #f59e0b;
  --color-error: #ef4444;
  --shadow-hover: 0 8px 30px rgba(0, 0, 0, 0.08);
  --focus-ring: 0 0 0 3px rgba(99, 102, 241, 0.12);
  color: var(--color-text);
  background: var(--color-background);
  font-family: "DM Sans", Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
  font-synthesis: none;
  text-rendering: optimizeLegibility;
}

* {
  box-sizing: border-box;
}

body {
  min-width: 320px;
  min-height: 100vh;
  margin: 0;
  background: var(--color-background);
}
```

- [ ] **Step 2: Replace typography and base controls**

Update the base element styles to:

```css
button,
input,
select,
textarea {
  font: inherit;
}

input,
select,
textarea {
  width: 100%;
  border: 1px solid var(--color-border);
  border-radius: 6px;
  padding: 10px 14px;
  color: var(--color-text);
  background: var(--color-surface);
  font-size: 0.875rem;
  transition:
    border-color 160ms ease,
    box-shadow 160ms ease;
}

input:focus,
select:focus,
textarea:focus {
  border-color: var(--color-primary);
  box-shadow: var(--focus-ring);
  outline: none;
}

textarea {
  resize: vertical;
}

a {
  color: var(--color-primary);
  font-weight: 700;
  text-decoration: none;
}

a:hover {
  color: var(--color-primary-hover);
}

h1,
h2,
h3,
p {
  margin-top: 0;
}

h1,
h2,
h3 {
  color: var(--color-text);
  font-family: "General Sans", "DM Sans", Inter, ui-sans-serif, system-ui, sans-serif;
  font-weight: 700;
  letter-spacing: -0.03em;
}
```

- [ ] **Step 3: Replace shell, navigation, and heading CSS**

Add or replace the shell styles with:

```css
.app-shell {
  width: min(1280px, calc(100% - 48px));
  margin: 0 auto;
  padding: 24px 0 48px;
}

.app-header {
  display: grid;
  gap: 32px;
  margin-bottom: 24px;
}

.app-nav {
  position: sticky;
  top: 16px;
  z-index: 10;
  display: flex;
  min-height: 56px;
  align-items: center;
  justify-content: space-between;
  gap: 24px;
  padding: 8px 12px;
  border: 1px solid var(--color-border);
  border-radius: 12px;
  background: rgba(255, 255, 255, 0.86);
  backdrop-filter: blur(16px);
}

.brand-lockup {
  display: inline-flex;
  align-items: center;
  gap: 10px;
  min-width: 0;
}

.brand-mark {
  display: inline-flex;
  width: 32px;
  height: 32px;
  align-items: center;
  justify-content: center;
  border-radius: 9999px;
  background: var(--color-text);
  color: var(--color-surface);
  font-family: "JetBrains Mono", monospace;
  font-size: 0.72rem;
  font-weight: 700;
}

.brand-name {
  overflow: hidden;
  color: var(--color-text);
  font-weight: 700;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.page-intro {
  max-width: 760px;
}

.eyebrow,
.section-kicker {
  margin: 0 0 10px;
  color: var(--color-neutral);
  font-size: 0.6875rem;
  font-weight: 700;
  letter-spacing: 0.12em;
  text-transform: uppercase;
}

h1 {
  max-width: 760px;
  margin-bottom: 12px;
  font-size: clamp(3rem, 7vw, 4.5rem);
  line-height: 0.95;
}

h2 {
  margin-bottom: 12px;
  font-size: clamp(2rem, 4vw, 3rem);
  line-height: 1;
}

h3 {
  margin-bottom: 10px;
  font-size: 1.25rem;
  line-height: 1.15;
}

.hero-copy,
.muted,
.empty-state {
  color: var(--color-text-secondary);
}

.hero-copy {
  max-width: 620px;
  margin-bottom: 0;
  font-size: 1rem;
  line-height: 1.6;
}
```

- [ ] **Step 4: Replace action, tab, and button CSS**

Use:

```css
.tabs,
.action-row {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.tabs {
  justify-content: flex-end;
}

.tab,
.primary-action,
.secondary-action,
.danger-action,
.text-action {
  min-height: 38px;
  border: 1px solid var(--color-border);
  border-radius: 6px;
  padding: 8px 14px;
  cursor: pointer;
  font-weight: 700;
  transition:
    transform 160ms ease,
    border-color 160ms ease,
    background 160ms ease,
    box-shadow 160ms ease,
    color 160ms ease;
}

.tab,
.secondary-action,
.text-action {
  color: var(--color-text);
  background: var(--color-surface);
}

.tab:hover,
.primary-action:hover,
.secondary-action:hover,
.danger-action:hover,
.text-action:hover {
  transform: translateY(-1px);
}

.tab[aria-pressed="true"],
.primary-action {
  border-color: var(--color-primary);
  color: var(--color-surface);
  background: var(--color-primary);
}

.primary-action:hover {
  border-color: var(--color-primary-hover);
  background: var(--color-primary-hover);
  box-shadow: 0 4px 12px rgba(99, 102, 241, 0.35);
}

.secondary-action:hover,
.tab:hover,
.text-action:hover {
  border-color: rgba(99, 102, 241, 0.45);
  color: var(--color-primary);
}

.danger-action {
  border-color: rgba(239, 68, 68, 0.35);
  color: var(--color-error);
  background: var(--color-surface);
}

.danger-action:hover {
  border-color: var(--color-error);
  color: var(--color-surface);
  background: var(--color-error);
}

.text-action {
  width: fit-content;
  margin-bottom: 20px;
}
```

- [ ] **Step 5: Replace layout, card, list, chip, candidate, review, and responsive CSS**

Update the remaining component CSS to match these rules:

```css
.workspace-grid {
  display: grid;
  grid-template-columns: minmax(300px, 0.85fr) minmax(0, 1.15fr);
  gap: 24px;
  margin-top: 24px;
}

.detail-grid {
  grid-template-columns: minmax(260px, 0.7fr) minmax(320px, 1fr);
}

.card {
  min-width: 0;
  padding: 24px;
  border: 1px solid var(--color-border);
  border-radius: 12px;
  background: var(--color-surface);
}

.card-form {
  background: var(--color-surface);
  color: var(--color-text);
}

.card-form .section-kicker,
.card-form .muted {
  color: var(--color-text-secondary);
}

.card-form input,
.card-form textarea,
.card-form select {
  color: var(--color-text);
  background: var(--color-surface);
}

.stack {
  display: grid;
  gap: 16px;
}

.stack label,
.card label {
  display: grid;
  gap: 8px;
  color: var(--color-text);
  font-weight: 700;
}

.split-heading {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
}

.split-heading span,
.rank-pill,
.score-badge {
  width: fit-content;
  border-radius: 9999px;
  padding: 4px 10px;
  color: var(--color-text-secondary);
  background: #f3f4f6;
  font-size: 0.75rem;
  font-weight: 700;
}

.job-list,
.rubric-list,
.refinement-grid,
.compact-list {
  display: grid;
  gap: 8px;
}

.list-row,
.rubric-item,
.candidate-card,
.refinement-card,
.evidence-card {
  border: 1px solid var(--color-border);
  border-radius: 12px;
  padding: 16px;
  background: var(--color-surface);
  transition:
    transform 200ms ease,
    border-color 200ms ease,
    box-shadow 200ms ease;
}

.list-row,
.candidate-card,
.refinement-card {
  text-align: left;
}

.list-row {
  width: 100%;
  display: flex;
  justify-content: space-between;
  gap: 16px;
}

.list-row:hover,
.candidate-card:hover,
.refinement-card:hover {
  transform: translateY(-2px);
  border-color: rgba(99, 102, 241, 0.35);
  box-shadow: var(--shadow-hover);
}

.list-row[aria-pressed="true"] {
  border-color: var(--color-primary);
  background: rgba(99, 102, 241, 0.06);
  box-shadow: var(--focus-ring);
}

.static-row {
  display: grid;
}

.rubric-list,
.candidate-grid,
.refinement-grid,
.review-block {
  margin-top: 18px;
}

.rubric-item {
  display: grid;
  gap: 8px;
}

.candidate-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(240px, 1fr));
  gap: 20px;
}

.candidate-card {
  display: grid;
  gap: 18px;
}

.review-block {
  display: grid;
  gap: 12px;
}

.score-badge {
  font-size: 1rem;
}

.evidence-grid {
  display: grid;
  gap: 10px;
}

.evidence-card {
  display: grid;
  gap: 6px;
}

.compact-list {
  padding-left: 20px;
}

@media (max-width: 820px) {
  .app-shell {
    width: min(100% - 32px, 1280px);
    padding-top: 16px;
  }

  .app-nav,
  .workspace-grid,
  .detail-grid {
    grid-template-columns: 1fr;
  }

  .app-nav {
    position: static;
    display: grid;
  }

  .card {
    padding: 20px;
  }

  .tabs {
    justify-content: flex-start;
  }

  h1 {
    font-size: 3rem;
  }
}
```

- [ ] **Step 6: Remove obsolete warm design selectors**

Search:

```bash
rg -n "#f3ead6|#fff9ea|#eadfc4|#dfe7d4|#1f321f|#eac077|radial-gradient|linear-gradient|border-radius: 30px|border-radius: 28px|box-shadow: 0 24px|box-shadow: 0 18px" frontend/src/App.css
```

Expected: no matches. If matches remain, replace them with the DESIGN.md tokens above.

- [ ] **Step 7: Run frontend tests**

Run:

```bash
cd frontend && npm run test
```

Expected: PASS.

- [ ] **Step 8: Commit the CSS refresh**

Run:

```bash
git add frontend/src/App.css
git commit -m "style: apply design md visual system"
```

Expected: commit contains the CSS refresh only, unless Task 2 was intentionally batched with it.

## Task 4: Verify Build, Lint, and Browser Rendering

**Files:**
- No required source edits unless verification exposes a visual defect.

- [ ] **Step 1: Run TypeScript lint**

Run:

```bash
cd frontend && npm run lint
```

Expected: PASS.

- [ ] **Step 2: Run production build**

Run:

```bash
cd frontend && npm run build
```

Expected: PASS.

- [ ] **Step 3: Ensure dev server is running**

Run:

```bash
curl -sS http://127.0.0.1:5173/ -o /dev/null -w '%{http_code}\n'
```

Expected: `200`. If it is not running, start it from the repo root:

```bash
bash scripts/dev.sh
```

- [ ] **Step 4: Browser-check primary views**

Open `http://localhost:5173` and verify:

- Jobs page has sticky nav, compact intro, white panels, 12px cards, 6px controls.
- Search page keeps two-column layout on desktop and stacks on mobile.
- Candidates grid has readable cards and hover elevation only.
- Candidate detail page remains usable and text does not overflow.
- Refinements page uses the same flat panel style.
- No warm gradient background, dark green form panel, or persistent heavy card shadow remains.

- [ ] **Step 5: Fix any verification-only CSS defects**

If browser verification shows overflow or spacing issues, modify only `frontend/src/App.css`. Typical fixes:

```css
.tab,
.primary-action,
.secondary-action,
.danger-action,
.text-action {
  white-space: normal;
}

.list-row,
.candidate-card,
.refinement-card {
  overflow-wrap: anywhere;
}
```

Run:

```bash
cd frontend && npm run test && npm run lint && npm run build
```

Expected: PASS.

- [ ] **Step 6: Commit verification fixes**

Run:

```bash
git add frontend/src/App.css
git commit -m "fix: polish design md responsive rendering"
```

Expected: commit only if Step 5 required source changes.

## Self-Review

Spec coverage:

- Source tokens and approved Editorial Ops direction are covered by Task 3.
- Shell and navigation refresh are covered by Task 2 and Task 3.
- Existing workflows and data flow stay unchanged by limiting edits to `App.tsx`, `App.css`, and optional shell test updates.
- Error/status styling is covered through shared muted/status component styles.
- Testing and browser verification are covered by Task 4.

Placeholder scan:

- No `TBD`, `TODO`, or incomplete implementation steps.

Type consistency:

- React markup uses existing `pages`, `page`, and `setPage` state from `App.tsx`.
- CSS class names introduced in Task 2 are defined in Task 3.


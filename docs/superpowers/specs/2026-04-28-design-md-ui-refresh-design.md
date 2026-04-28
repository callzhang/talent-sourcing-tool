# DESIGN.md UI Refresh Design

Date: 2026-04-28

Status: Ready for user review

## Purpose

Update the Talent Sourcing Tool visual design to follow `DESIGN.md` using the approved `Editorial Ops` direction.

The goal is to make the app feel like a precise, modern operating workspace: editorial typography, flat white panels, subtle borders, high scan density, and restrained interaction states. The product structure should stay the same.

## Source Design

The source style is `DESIGN.md` / Genesis:

- background `#FAFAFA`;
- surface `#FFFFFF`;
- primary interaction color `#6366F1`;
- hover primary `#4F46E5`;
- text primary `#0A0A0A`;
- text secondary `#6B6B6B`;
- muted neutral `#9C9C9C`;
- border `#E8E8EC`;
- semantic success, warning, and error colors;
- General Sans for headings, DM Sans for body, JetBrains Mono for code-like values;
- flat cards with borders, hover-only elevation;
- 6px buttons and inputs, 12px cards;
- no decorative gradients or persistent shadows.

## Approved Direction

Use `Editorial Ops`.

This adapts Genesis to a recruiting workflow instead of copying the original design-system-gallery context. The UI should keep its current working pages and make them feel more structured, readable, and operational.

Rejected directions:

- `Gallery System`: too literal to the original community-platform concept and less efficient for repeated sourcing work.
- `Command Center`: efficient but less aligned with the bold editorial personality in `DESIGN.md`.

## Scope

In scope:

- Global visual tokens in `frontend/src/App.css`.
- Font loading for General Sans, DM Sans, and JetBrains Mono.
- Header/navigation restyle.
- Card, form, list, chip, button, input, and link restyle.
- Responsive spacing and layout cleanup.
- Light adjustments to `frontend/src/App.tsx` if needed for sticky navigation and compact title hierarchy.
- Keep existing pages, API calls, state, and workflows unchanged.

Out of scope:

- New product behavior.
- New pages.
- Backend changes.
- Routing changes.
- Real Bright Data connector implementation.
- New icon library adoption.
- Dark mode, unless already trivial through tokens.

## UI Architecture

### Shell

Replace the current rounded warm hero block with a more operational shell:

- sticky top nav, 56px tall;
- white or translucent white surface with backdrop blur;
- 1px bottom border;
- product name on the left;
- tab buttons on the right or center depending on viewport;
- compact page intro below the nav.

The app should still use one React state machine for pages. No router is required for this refresh.

### Layout

Keep the current page layouts:

- `JobsPage`: two-column JD intake plus active rubric.
- `SearchPage`: two-column search form plus run history and latest candidates.
- `CandidatesPage`: full-width candidate review queue grid.
- `CandidateDetailPage`: existing review detail workflow.
- `RefinementsPage`: two-column selector plus suggestions.

Update spacing to the 4px scale:

- container max width around 1280px;
- 24px horizontal padding on desktop;
- 32-48px major section spacing;
- 20-24px card grid gaps.

### Components

Buttons:

- primary: indigo fill, white text, 6px radius;
- secondary: white/transparent background, border, 6px radius;
- text/ghost: no filled pill shape;
- destructive: red border/text or red fill where destructive confirmation is direct;
- all buttons move up 1px on hover;
- one primary button per view section.

Cards and panels:

- white surface;
- 1px `#E8E8EC` border;
- 12px radius for main cards;
- no static shadow;
- hover shadow only for clickable/repeated cards, using `0 8px 30px rgba(0,0,0,0.08)`.

Forms:

- 6px input radius;
- 1px border;
- 10px vertical and 14px horizontal padding;
- focus border indigo plus `0 0 0 3px rgba(99,102,241,0.12)`;
- no dark inverted form panel.

Lists:

- rows use subtle dividers and white surfaces;
- selected row uses indigo border/ring or light indigo background;
- status/rank chips use pill shape with semantic or neutral colors.

Typography:

- headings use General Sans, bold;
- body uses DM Sans;
- code-like IDs, provider names, and technical values use JetBrains Mono;
- avoid viewport-scaled font sizes except responsive clamps for top-level display.

## Data Flow

No data flow changes.

The refresh is presentation-only:

- existing API client stays unchanged;
- backend schema stays unchanged;
- page state stays unchanged;
- candidate review and decision logic stay unchanged.

## Error Handling

No behavioral error handling changes.

Existing status messages should become visually consistent with the new system:

- neutral status: secondary text;
- success: success color chip or subtle text;
- warning: warning color chip or banner if already present;
- error: error color and input border where relevant.

Do not add fallback logic or new try/catch behavior for this visual refresh.

## Testing

Run frontend verification:

- `npm run lint`;
- `npm run test`;
- `npm run build`.

Browser verification:

- load `http://localhost:5173`;
- inspect desktop layout;
- inspect mobile/narrow viewport;
- verify Jobs, Search, Candidates, Candidate Detail, and Refinements still render;
- confirm text does not overflow buttons/cards;
- confirm no old warm gradients or persistent heavy shadows remain.

## Implementation Notes

Prefer a scoped CSS refresh over broad component rewrites.

Expected edit set:

- `frontend/src/App.css`;
- `frontend/src/App.tsx` only if the existing header markup cannot support the sticky nav and compact page intro with CSS alone;
- only touch page components if a class name or small wrapper is required for layout.

Avoid unrelated refactors. Keep the existing interaction model stable.

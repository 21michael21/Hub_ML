# Hub_ML Dashboard QA Report

Final status: `PASS`

Screenshots:
- `screenshots/dashboard-desktop.png`
- `screenshots/dashboard-mobile.png`

## Pages Updated

- `/` now renders the production dashboard.
- `/dashboard` renders the same production dashboard.
- `/hubml-preview` remains as the reference preview page for visual comparison.

## What Matches The Hub_ML Reference

- Dark engineering console visual direction.
- Exact Hub_ML token palette from `DESIGN_SPEC_HUBML.md`.
- `Space Grotesk`, `IBM Plex Sans`, and `IBM Plex Mono`.
- Sticky `TopIdeBar` with 44px height, dark translucent background, blur, breadcrumb, reload pill, and command palette pill.
- Sticky `BottomStatusBar` with 34px height, dark translucent background, blur, mono status groups.
- Main dashboard width `760px` with `40px 28px` page padding.
- Hero/header rhythm and QualityGate-style card.
- Clickable cards use `#12151D`, `#313A48`, 12px radius, right arrow affordance, and hover `translateY(-2px)`.
- Status chips use dot colors for READY, PASS/DONE, IN PROGRESS/P1, FAIL/BLOCKED/ERROR, and muted P3/default states.
- Loading state uses shimmer skeleton blocks with `hubShimmer 1.5s linear infinite`.
- Animation sequence uses `hubFadeUp` with section delays and card delays.
- Mobile layout stacks into one column and has no horizontal overflow at 390px.
- Final CSS check confirms body background `#0A0C11`, text `#F1F3F8`, body font `IBM Plex Sans`, 14px base size, 1.5 line-height.
- Final DOM check confirms topbar 44px, bottombar 34px, main width 760px, main gap 32px, card background `#12151D`, card border `#313A48`, card radius 12px, chip background `#1A1F29`, chip radius 999px.

## Final Fixes

- Set `.hub-main` to `display:flex`, `flex-direction:column`, and `gap:32px`.
- Removed extra vertical section spacing by setting `.hub-hero` bottom margin and `.hub-section` top margin to `0`; section rhythm now comes from main gap.
- Adjusted the fourth card stagger delay to `.37s` to match the reference sequence.
- Saved desktop and mobile screenshots in `screenshots/`.

## Intentional Differences

- Today data is shown as a designed empty state because the current web app has no safe API layer for Trello/Google Calendar data.
- Reload is a visual loading state. It does not call Trello or Google Calendar because credentials must not be exposed to the browser bundle.
- In Progress cards are static representative cards until a backend/API layer is added.
- Command palette is a disabled visual affordance; no shortcut system exists in the web app yet.

## Old UI Remaining

- No older frontend pages were found before this work.
- The previous `/hubml-preview` remains intentionally as a reference page.
- Python CLI output is unchanged and still has its original terminal formatting.

## Components Used

- `AppShell`
- `TopIdeBar`
- `BottomStatusBar`
- `StatusChip`
- `MetricTile`
- `ClickableCard`
- `SectionHeader`
- `SkeletonBlock`
- `QualityGateCard`
- `EmptyState`

## Verification

Commands run from `web/`:

```bash
npm run build
npm run lint
```

Both passed.

Backend test command run from project root:

```bash
python3 -m pytest
```

Result: `collected 0 items`, so this project copy has no Python tests to run.

Browser QA:

- Opened `http://127.0.0.1:5173/dashboard`.
- Verified body background `rgb(10, 12, 17)`.
- Verified `TopIdeBar`, `BottomStatusBar`, `QualityGateCard`, reload pill, command palette pill, empty state, and 6 clickable cards.
- Clicked reload and verified loading text plus 18 shimmer skeleton blocks.
- Checked 390px mobile viewport: no horizontal overflow.
- Checked 1440px desktop viewport: no horizontal overflow, topbar 44px, statusbar 34px.

## Remaining Work

- Add a backend/API layer if the dashboard must show live Trello/Google Calendar cards.
- Keep OAuth tokens and Google/Trello credentials server-side only.
- Wire command palette only after real commands/shortcuts are defined.

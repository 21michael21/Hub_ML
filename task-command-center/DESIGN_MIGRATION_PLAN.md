# Hub_ML Design Migration Plan

## Current Project Stack

- Existing project is Python CLI/backend-oriented.
- Main command file: `taskctl.py`
- Business modules: `src/`
- Tests, when present in this copy, should target CLI behavior.
- No existing frontend was found: no `package.json`, `vite.config.*`, `src/**/*.tsx`, or existing app router.

Decision: create an isolated frontend in `web/` using Vite + React + TypeScript + plain CSS. Do not change Python CLI, Trello logic, Google Calendar logic, `.env`, `client_secret.json`, `token.json`, or credentials.

## UI Files To Add

- `web/package.json`
- `web/index.html`
- `web/vite.config.ts`
- `web/tsconfig.json`
- `web/tsconfig.node.json`
- `web/src/main.tsx`
- `web/src/App.tsx`
- `web/src/styles/hubml.css`
- `web/src/components/AppShell.tsx`
- `web/src/components/TopIdeBar.tsx`
- `web/src/components/BottomStatusBar.tsx`
- `web/src/components/StatusChip.tsx`
- `web/src/components/MetricTile.tsx`
- `web/src/components/ClickableCard.tsx`
- `web/src/components/SectionHeader.tsx`
- `web/src/components/SkeletonBlock.tsx`
- `web/src/components/QualityGateCard.tsx`
- `web/src/components/EmptyState.tsx`
- `web/src/pages/HubMLPreview.tsx`

## Where Styles Will Live

Global Hub_ML tokens and component classes live in:

`web/src/styles/hubml.css`

This file owns:
- CSS variables
- font imports
- base body styles
- keyframes
- AppShell layout
- reusable Hub_ML component classes

## Components To Create

- AppShell
- TopIdeBar
- BottomStatusBar
- StatusChip
- MetricTile
- ClickableCard
- SectionHeader
- SkeletonBlock
- QualityGateCard
- EmptyState

## Pages To Build

First page:
- `/hubml-preview`

Preview content adapts Hub_ML Home to this project:
- Brand: `Task Command Center`
- Kicker: `· local workstation`
- Description: `Консоль управления задачами, Trello и Google Calendar.`
- QualityGate: `100%`, `SYSTEM GATE`, `READY`, `Trello + Google Calendar connected`
- Resume cards:
  - `Trello board sync` — `READY`
  - `Google Calendar reminders` — `READY`
  - `Inbox review` — `IN PROGRESS`
- Today cards:
  - `Создать реальные задачи`
  - `Проверить календарные блоки`

Later migration:
- Replace or wrap any future real task dashboard with these primitives.
- Keep CLI output and backend behavior unchanged.
- Feed real Trello/Google state into cards only after preview is visually accepted.

## Risks

- The current project has no frontend, so `web/` is a new surface with separate dependencies.
- The preview is static by design; connecting live Trello/Google state later must not expose tokens or credentials to browser code.
- OAuth credentials must stay server/CLI-side. Do not bundle `.env`, `client_secret.json`, `token.json`, or config secrets into Vite.
- Styling must not drift into generic Tailwind slate/zinc palettes; use only Hub_ML tokens from `DESIGN_SPEC_HUBML.md`.

## Verification Commands

From `web/`:

```bash
npm install
npm run build
npm run lint
```

Run `npm run dev` only for local browser preview:

```bash
npm run dev -- --host 127.0.0.1
```

Backend safety check from project root:

```bash
python3 -m pytest
```

If tests are not installed in this copy, report that explicitly and do not alter CLI code just to satisfy frontend work.

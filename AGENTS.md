## Agent skills

### Issue tracker

Issues live in this repo's GitHub Issues (via `gh`). See `docs/agents/issue-tracker.md`.

### Triage labels

Uses the default five-role vocabulary (`needs-triage`, `needs-info`, `ready-for-agent`, `ready-for-human`, `wontfix`). See `docs/agents/triage-labels.md`.

### Domain docs

Single-context layout: root `CONTEXT.md` + `docs/adr/`. See `docs/agents/domain.md`.

### UX constitution

Every page, route, tab, and major panel transition must preserve visual continuity. Keep the current shell visible, provide an immediate loading/transition state, animate content and layout changes with the shared motion language, and honor `prefers-reduced-motion`; a blank flash or abrupt hard swap is not complete.

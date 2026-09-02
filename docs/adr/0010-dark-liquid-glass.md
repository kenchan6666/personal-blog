# Dark liquid-glass theme

Owner asked for a **visitor-controlled dark theme** after ADR-0009 shipped light-only. Public and admin UI keep the same liquid-glass language (pastel orbs, frosted panels, coral CTAs) and swap token values under `html[data-theme="dark"]`. Preference is stored in `localStorage` (`site-theme`) and applied before paint to avoid a flash.

This amends ADR-0009’s “no theme switcher in v1” clause. Do not revive the superseded Digicrypt deep-purple shell (ADR-0006).

Tokens and do/don’t: `docs/design/VISUAL.md`.

## Problem Statement

I need a job-seeking personal site that looks premium, shows who I am and what I have built first, then supports Journals and Articles. I must edit all public content myself through a private CMS, optionally attach GitHub repos to Projects with a GitHub-like source browser, support Traditional Chinese (default) and English UI chrome, and deploy everything on a single VM behind nginx.

## Solution

Build a Personal Portfolio: Next.js public + Owner admin UI, FastAPI/Beanie/Mongo system of record, Redis for OTP/session and GitHub API cache. Visitors see Published Profile, Projects, Journals, Articles, and moderated Comments. The Owner signs in with email OTP, manages all entities in the CMS, links SourceRepos via GitHub OAuth, and publishes when ready. Visual system follows light flat liquid glass (see `docs/design/VISUAL.md`, ADR-0009).

## Testing Seams

- **Primary seam:** Portfolio HTTP API (FastAPI) — all public read, Owner auth/CMS, comments, and GitHub source-browse behavior tested at this HTTP/JSON boundary.
- **Deferred:** Next.js Playwright for Hero/i18n/routing (after shell exists).

## User Stories

1. As a visitor, I want the homepage to lead with who the Owner is and featured work, so that I immediately understand fit for hiring.
2. As a visitor, I want a clear brand name at hero level, so that the site feels like a deliberate personal product, not a generic template.
3. As a visitor, I want a short positioning line and supporting sentence on the hero, so that I grasp the Owner’s focus in seconds.
4. As a visitor, I want CTAs to Projects and Articles from the hero, so that I can dive into evidence quickly.
5. As a visitor, I want a dominant hero visual (not a dashboard of widgets), so that the first viewport feels composed and premium.
6. As a visitor, I want a glass sidebar with Projects, Articles, Journals, and language switch, so that navigation stays consistent.
7. As a mobile visitor, I want the sidebar to become a drawer, so that the layout remains usable on small screens.
8. As a visitor, I want the default locale to be Traditional Chinese (`zh-Hant`), so that the primary audience sees the intended chrome first.
9. As a visitor, I want to switch UI chrome to English, so that international recruiters can navigate comfortably.
10. As a visitor, I want Owner-authored titles and Markdown bodies shown exactly as written, so that nothing is auto-translated or invented.
11. As a visitor, I want to open a Profile summary (avatar, bio, skills, experience, public email, Links), so that I can contact and evaluate the person.
12. As a visitor, I want ordered Links on the Profile (GitHub, LinkedIn, resume PDF, etc.), so that I can jump to external proof.
13. As a visitor, I want a Projects index of only Published projects the Owner added to the site, so that I am not flooded with every GitHub repo.
14. As a visitor, I want a Project detail with Owner Markdown description, so that I understand motivation, role, and outcomes.
15. As a visitor, I want an optional related Article link from a Project context, so that I can read deeper write-ups.
16. As a visitor, I want a GitHub-like read-only source browser on a Project with a public SourceRepo (README, branch switch, deep tree, file blob), so that I can evaluate code without leaving the site.
17. As a visitor, I must not receive tree/blob content for private SourceRepos, so that private code is never leaked through the site.
18. As a visitor, I want Journals listed and readable when Published, so that I can see day-to-day writing.
19. As a visitor, I want Articles listed and readable when Published, so that I can see technical or project-depth writing.
20. As a visitor, I want an Article to optionally show a related Project, so that writing and portfolio connect.
21. As a visitor, I want Journals not tied to Projects, so that daily writing stays separate from portfolio entities.
22. As a visitor, I want to submit a Comment on a Journal or Article with display name and email, so that I can leave feedback without creating an account.
23. As a visitor, I want my email hidden from public Comment display, so that I am not exposed to scrapers.
24. As a visitor, I want only approved Comments to appear, so that the hiring-facing site stays clean.
25. As a visitor, I want to see Owner replies on Comments, so that conversation can continue in-site.
26. As a visitor, I do not want Comments on Project pages, so that portfolio evaluation stays focused.
27. As a visitor, I do not want an in-site private messaging form, so that contact stays via Links and public email.
28. As a visitor, I want Draft content to be invisible (404), so that unfinished work never leaks.
29. As a visitor, I want image uploads limited to Profile avatar (other images via Markdown URLs), so that the media surface stays small.
30. As a visitor, I want light liquid-glass visuals with coral CTAs and restrained pixel accents, so that the site feels distinctive but professional and easy to read.
31. As a visitor, I want motion that aids hierarchy (hero entrance, glass hover, short route fade) and respects reduced-motion, so that polish does not harm accessibility.
32. As the Owner, I want email OTP login to my allowlisted mailbox only, so that only I can administer the site.
33. As the Owner, I want OTP codes delivered via SMTP from my configured mailbox, so that I can sign in without passwords.
34. As the Owner, I want Redis-backed short-lived OTP/session and rate limits, so that auth stays safe under retries.
35. As the Owner, I want a CMS for Profile, Links, Projects, Journals, Articles, and Comments, so that I can update the public site without redeploying for content.
36. As the Owner, I want Draft and Published states for Journals, Articles, and Projects, so that I can prepare content before release.
37. As the Owner, I want to author long-form fields in Markdown, so that writing stays engineer-friendly.
38. As the Owner, I want to upload a Profile avatar, so that the hero/profile shows my image.
39. As the Owner, I want to connect GitHub via OAuth App, so that I can pick repositories without pasting a PAT into production.
40. As the Owner, I want the CMS to list all my GitHub repositories I can access, so that I can choose what to feature.
41. As the Owner, I want to create a Project by selecting a GitHub repo then writing my own description, so that portfolio narrative stays mine.
42. As the Owner, I want only explicitly added Projects to appear publicly, so that GitHub inventory ≠ public portfolio.
43. As the Owner, I want SourceRepo browsing for public repos on the public site (depth B), so that candidates’ code is reviewable in-product.
44. As the Owner, I want private repos usable for CMS metadata without public tree/blob proxying, so that I do not accidentally publish secrets.
45. As the Owner, I want GitHub API responses cached in Redis, so that rate limits and latency stay manageable.
46. As the Owner, I want to approve or reject pending Comments, so that spam never goes live unchecked.
47. As the Owner, I want to reply to Comments as Owner, so that I can engage thoughtfully.
48. As the Owner, I want admin UI in the same visual language but denser, so that the CMS itself demonstrates craft.
49. As the Owner, I want the stack to run on one VM behind nginx (Next.js, FastAPI/uvicorn, Mongo, Redis), so that operations stay simple for a solo portfolio.
50. As a recruiter, I want the overall experience to feel elegant and intentional, so that the site itself is evidence of taste and engineering judgment.

## Implementation Decisions

- **Testing seam:** Portfolio HTTP API is the single primary seam; persistence and third-party clients sit behind it.
- **Modules:** `frontend` (Next.js App Router, public + `/admin`), `backend` (FastAPI + Beanie), infra on one VM (nginx, MongoDB, Redis) per ADR-0003/0004/0008.
- **Domain entities:** Profile, Link, Project, Journal, Article, Comment, Owner, SourceRepo, Draft/Published — vocabulary from `CONTEXT.md`.
- **i18n:** Shell dictionaries `zh-Hant` (default) and `en`; content fields opaque Owner strings.
- **Auth:** Email OTP only; allowlist Owner email (`ynchanhk@gmail.com`); SMTP send from that mailbox; sessions in Redis.
- **GitHub:** OAuth App; public source browser via API (no full mirror) per ADR-0001; private tree/blob never proxied to visitors.
- **Comments:** Journal + Article only; name+email; moderation required; Owner replies allowed — ADR-0007.
- **Media:** Avatar upload only in v1; other images via Markdown URLs.
- **Visual:** Tokens and Hero rules in `docs/design/VISUAL.md` / ADR-0009 (supersedes ADR-0006); pixel accents only.
- **Routes (public v1):** `/`, `/projects`, `/projects/[slug]`, `/articles`, `/articles/[slug]`, `/journals`, `/journals/[slug]`, locale switch, `/admin/*`. No standalone about page; no site DM form.
- **API shape (conceptual):** versioned JSON under `/api/...` for public reads and Owner mutations; GitHub OAuth callback on backend; source browser endpoints scoped to Published public SourceRepos.

## Testing Decisions

- Good tests assert external behavior at the HTTP API: status codes, auth gates, Published vs Draft visibility, comment moderation, private SourceRepo non-leakage, OTP rate limits — not Beanie query shapes or Redis key names.
- Modules under test: FastAPI route handlers / application services exposed through the API seam.
- Prior art: none yet (greenfield); establish API integration tests first, UI e2e later.

## Out of Scope

- Multi-Owner or role systems
- In-site private messaging
- Auto-translation of Owner content
- Full GitHub UI clone (Issues/PRs/Actions)
- Mirroring entire git repositories into Mongo
- General-purpose media library / image CDN beyond avatar (v1)
- Split multi-host CDN architecture (deferred)
- Comments on Projects
- Pixel-first / retro-OS whole-site theme

## Further Notes

- Immediate follow-on after this spec: scaffold Next.js shell and land homepage Hero per `VISUAL.md` (static chrome; API wiring later).
- Issue tracker: GitHub Issues; triage label `ready-for-agent`.
- Design references: Hero two-column + capsule CTA only from `docs/design/references/hero-mood-digicrypt-purple.png` (color temperature no longer applies; see ADR-0009).

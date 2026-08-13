# Project source via GitHub API (no mirror)

Projects may bind a SourceRepo. The public “GitHub-like” view is a **read-only browser** (README, branch switch, tree navigation, file blob) fed by the GitHub API through Owner OAuth — we do **not** clone or store full repository contents in Mongo. Caching (e.g. Redis) may hold API responses for speed/rate-limits, but Mongo remains the system of record for Portfolio entities (Profile, Project metadata, Journals, Articles), not for git objects.

**Private repositories:** the Owner may browse them in the CMS and attach metadata, but the public site must **not** proxy tree/blob contents for private repos (description + link to GitHub only). Publishing must not leak private source via the site token.
